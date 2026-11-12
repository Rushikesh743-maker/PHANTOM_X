import uuid
import csv
import io
import json
import logging
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc, delete, func
from fastapi import HTTPException, status

from app.models.application import Application
from app.models.endpoint import DiscoveredEndpoint, EndpointRelationship
from app.inventory import (
    ApiClassifier,
    ApiCategory,
    CATEGORY_LABELS,
    ResourceMapper,
    RelationshipBuilder,
    RelationshipType,
    RelationshipProvenance,
)
from shared.enums.common import HttpMethod

logger = logging.getLogger("phantom_x.inventory_service")


class InventoryService:
    """
    Core service managing API inventory categorization, resource hierarchies,
    relationship and dependency mapping, statistics, and exports.
    """

    @classmethod
    async def validate_app_ownership(
        cls,
        db: AsyncSession,
        app_id: uuid.UUID,
        org_id: uuid.UUID
    ) -> Application:
        """
        Validates target application existence and verifies organization ownership.
        Returns 404 to avoid information leakage for cross-tenant attempts.
        """
        result = await db.execute(
            select(Application).where(
                and_(
                    Application.id == app_id,
                    Application.organization_id == org_id
                )
            )
        )
        app = result.scalars().first()
        if not app:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application not found or unauthorized access"
            )
        return app

    @classmethod
    def classify_and_tag_endpoint(cls, ep: DiscoveredEndpoint) -> Dict[str, Any]:
        """
        Runs the ApiClassifier and ResourceMapper on an endpoint and enriches its raw_metadata.
        """
        method_str = ep.method.value if hasattr(ep.method, "value") else str(ep.method)
        raw_meta = dict(ep.raw_metadata or {})

        # 1. Classification
        classification = ApiClassifier.classify(
            path=ep.path,
            method=method_str,
            tags=raw_meta.get("tags"),
            operation_id=raw_meta.get("operation_id"),
            description=raw_meta.get("description"),
            parameters=ep.parameters,
            raw_metadata=raw_meta,
        )

        raw_meta["category"] = classification["category"]
        raw_meta["category_label"] = classification["category_label"]
        raw_meta["category_confidence"] = classification["confidence"]
        raw_meta["category_explanation"] = classification["explanation"]
        raw_meta["category_provenance"] = classification["provenance"]

        # 2. Resource Mapping
        res_name, parent_res, res_conf, res_ev = ResourceMapper.extract_resource(ep.path)
        raw_meta["resource_name"] = res_name
        raw_meta["parent_resource_name"] = parent_res
        raw_meta["resource_confidence"] = res_conf
        raw_meta["resource_evidence"] = res_ev

        ep.raw_metadata = raw_meta
        return raw_meta

    @classmethod
    async def rebuild_inventory_mappings(
        cls,
        db: AsyncSession,
        app_id: uuid.UUID,
        org_id: uuid.UUID
    ) -> Dict[str, Any]:
        """
        Classifies all endpoints for an application, maps resources,
        and regenerates deduplicated endpoint relationships.
        """
        app = await cls.validate_app_ownership(db, app_id, org_id)

        # 1. Fetch all endpoints for this application
        result = await db.execute(
            select(DiscoveredEndpoint).where(DiscoveredEndpoint.application_id == app.id)
        )
        endpoints = result.scalars().all()

        if not endpoints:
            return {
                "application_id": app.id,
                "endpoints_classified": 0,
                "relationships_created": 0,
                "unique_resources": 0,
                "message": "No endpoints available for mapping"
            }

        endpoint_dicts = []
        unique_resources = set()

        # 2. Classify and enrich each endpoint
        for ep in endpoints:
            cls.classify_and_tag_endpoint(ep)
            unique_resources.add(ep.raw_metadata.get("resource_name", "root"))
            endpoint_dicts.append({
                "id": str(ep.id),
                "path": ep.path,
                "method": ep.method.value if hasattr(ep.method, "value") else str(ep.method),
                "auth_required": ep.auth_required,
                "parameters": ep.parameters,
                "raw_metadata": ep.raw_metadata,
                "source": ep.raw_metadata.get("discovery_source", "openapi"),
            })

        # 3. Generate relationships
        inferred_relationships = RelationshipBuilder.build_relationships(
            endpoints=endpoint_dicts,
            application_id=app.id
        )

        # 4. Clear existing relationships for this application
        await db.execute(
            delete(EndpointRelationship).where(EndpointRelationship.application_id == app.id)
        )

        # 5. Insert new relationships
        rel_entities = []
        for rel in inferred_relationships:
            entity = EndpointRelationship(
                application_id=app.id,
                source_endpoint_id=uuid.UUID(str(rel["source_endpoint_id"])),
                target_endpoint_id=uuid.UUID(str(rel["target_endpoint_id"])),
                relationship_type=rel["relationship_type"],
                evidence_source=rel["evidence_source"],
                confidence=rel["confidence"],
                explanation=rel["explanation"],
                provenance=rel["provenance"],
                raw_metadata=rel.get("raw_metadata", {})
            )
            rel_entities.append(entity)

        if rel_entities:
            db.add_all(rel_entities)

        await db.commit()

        return {
            "application_id": app.id,
            "endpoints_classified": len(endpoints),
            "relationships_created": len(rel_entities),
            "unique_resources": len(unique_resources),
            "message": f"Successfully mapped {len(endpoints)} endpoints into {len(unique_resources)} resources and {len(rel_entities)} relationships."
        }

    @classmethod
    async def list_inventory(
        cls,
        db: AsyncSession,
        app_id: uuid.UUID,
        org_id: uuid.UUID,
        resource: Optional[str] = None,
        category: Optional[str] = None,
        method: Optional[str] = None,
        source: Optional[str] = None,
        search: Optional[str] = None,
        unclassified_only: bool = False,
        incomplete_metadata_only: bool = False,
        skip: int = 0,
        limit: int = 100
    ) -> List[DiscoveredEndpoint]:
        """
        Lists endpoints for an application with rich filtering on resource,
        category, HTTP method, source, text search, and completeness.
        """
        await cls.validate_app_ownership(db, app_id, org_id)

        query = select(DiscoveredEndpoint).where(DiscoveredEndpoint.application_id == app_id)

        if method:
            try:
                http_m = HttpMethod(method.upper())
                query = query.where(DiscoveredEndpoint.method == http_m)
            except ValueError:
                pass

        query = query.order_by(DiscoveredEndpoint.path.asc())
        result = await db.execute(query)
        endpoints = result.scalars().all()

        # In-memory filtering for JSON-based metadata fields
        filtered: List[DiscoveredEndpoint] = []
        for ep in endpoints:
            meta = ep.raw_metadata or {}

            # Resource filter
            if resource and meta.get("resource_name") != resource.lower():
                continue

            # Category filter
            if category and meta.get("category") != category.upper():
                continue

            # Source filter
            if source:
                src_upper = source.upper()
                ep_src = (meta.get("discovery_source") or "").upper()
                sources_list = [s.upper() for s in meta.get("discovery_sources", [])]
                if src_upper != ep_src and src_upper not in sources_list:
                    continue

            # Search across path, resource, operation_id, description
            if search:
                s_lower = search.lower()
                op_id = (meta.get("operation_id") or "").lower()
                desc = (meta.get("description") or "").lower()
                res_n = (meta.get("resource_name") or "").lower()
                if (s_lower not in ep.path.lower() and
                    s_lower not in op_id and
                    s_lower not in desc and
                    s_lower not in res_n):
                    continue

            # Unclassified filter
            if unclassified_only:
                if meta.get("category") != ApiCategory.UNCLASSIFIED:
                    continue

            # Incomplete metadata filter
            if incomplete_metadata_only:
                has_desc = bool(meta.get("description"))
                has_params = bool(ep.parameters and len(ep.parameters) > 0)
                has_responses = bool(ep.response_codes and len(ep.response_codes) > 0)
                if has_desc and has_params and has_responses:
                    continue

            filtered.append(ep)

        return filtered[skip : skip + limit]

    @classmethod
    async def get_resource_groups(
        cls,
        db: AsyncSession,
        app_id: uuid.UUID,
        org_id: uuid.UUID
    ) -> List[Dict[str, Any]]:
        """
        Retrieves logical resource groups with method coverage, parameter summaries,
        and child-parent hierarchical relationships.
        """
        await cls.validate_app_ownership(db, app_id, org_id)

        result = await db.execute(
            select(DiscoveredEndpoint).where(DiscoveredEndpoint.application_id == app_id)
        )
        endpoints = result.scalars().all()

        ep_dicts = []
        for ep in endpoints:
            ep_dicts.append({
                "id": str(ep.id),
                "path": ep.path,
                "method": ep.method.value if hasattr(ep.method, "value") else str(ep.method),
                "parameters": ep.parameters,
                "source": ep.raw_metadata.get("discovery_source", "openapi"),
                "raw_metadata": ep.raw_metadata,
            })

        return ResourceMapper.group_by_resource(ep_dicts)

    @classmethod
    async def get_relationships(
        cls,
        db: AsyncSession,
        app_id: uuid.UUID,
        org_id: uuid.UUID,
        endpoint_id: Optional[uuid.UUID] = None,
        relationship_type: Optional[str] = None,
        provenance: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Retrieves stored endpoint relationships for an application,
        enriched with source/target path and method information.
        """
        await cls.validate_app_ownership(db, app_id, org_id)

        query = select(EndpointRelationship).where(EndpointRelationship.application_id == app_id)

        if endpoint_id:
            query = query.where(
                or_(
                    EndpointRelationship.source_endpoint_id == endpoint_id,
                    EndpointRelationship.target_endpoint_id == endpoint_id
                )
            )

        if relationship_type:
            query = query.where(EndpointRelationship.relationship_type == relationship_type.upper())

        if provenance:
            query = query.where(EndpointRelationship.provenance == provenance.lower())

        query = query.order_by(desc(EndpointRelationship.confidence)).offset(skip).limit(limit)

        result = await db.execute(query)
        relationships = result.scalars().all()

        # Fetch endpoint map for path and method enrichment
        ep_ids = set()
        for r in relationships:
            ep_ids.add(r.source_endpoint_id)
            ep_ids.add(r.target_endpoint_id)

        ep_map = {}
        if ep_ids:
            ep_res = await db.execute(
                select(DiscoveredEndpoint).where(DiscoveredEndpoint.id.in_(list(ep_ids)))
            )
            for ep in ep_res.scalars().all():
                ep_map[ep.id] = {
                    "path": ep.path,
                    "method": ep.method.value if hasattr(ep.method, "value") else str(ep.method)
                }

        formatted = []
        for r in relationships:
            src = ep_map.get(r.source_endpoint_id, {})
            tgt = ep_map.get(r.target_endpoint_id, {})
            formatted.append({
                "id": r.id,
                "application_id": r.application_id,
                "source_endpoint_id": r.source_endpoint_id,
                "target_endpoint_id": r.target_endpoint_id,
                "source_endpoint_path": src.get("path"),
                "source_endpoint_method": src.get("method"),
                "target_endpoint_path": tgt.get("path"),
                "target_endpoint_method": tgt.get("method"),
                "relationship_type": r.relationship_type,
                "evidence_source": r.evidence_source,
                "confidence": r.confidence,
                "explanation": r.explanation,
                "provenance": r.provenance,
                "raw_metadata": r.raw_metadata or {},
                "created_at": r.created_at
            })

        return formatted

    @classmethod
    async def get_inventory_stats(
        cls,
        db: AsyncSession,
        app_id: uuid.UUID,
        org_id: uuid.UUID
    ) -> Dict[str, Any]:
        """
        Computes accurate statistics directly from database records.
        """
        await cls.validate_app_ownership(db, app_id, org_id)

        result = await db.execute(
            select(DiscoveredEndpoint).where(DiscoveredEndpoint.application_id == app_id)
        )
        endpoints = result.scalars().all()

        rel_result = await db.execute(
            select(EndpointRelationship).where(EndpointRelationship.application_id == app_id)
        )
        relationships = rel_result.scalars().all()

        method_dist: Dict[str, int] = {}
        category_dist: Dict[str, int] = {}
        source_dist: Dict[str, int] = {}
        unique_resources: set = set()

        documented_count = 0
        observed_count = 0
        imported_count = 0
        unclassified_count = 0
        incomplete_count = 0

        for ep in endpoints:
            m = ep.method.value if hasattr(ep.method, "value") else str(ep.method)
            method_dist[m] = method_dist.get(m, 0) + 1

            meta = ep.raw_metadata or {}
            cat = meta.get("category", ApiCategory.UNCLASSIFIED)
            category_dist[cat] = category_dist.get(cat, 0) + 1
            if cat == ApiCategory.UNCLASSIFIED:
                unclassified_count += 1

            res = meta.get("resource_name") or ResourceMapper.extract_resource(ep.path)[0]
            unique_resources.add(res)

            src = (meta.get("discovery_source") or "OPENAPI").upper()
            source_dist[src] = source_dist.get(src, 0) + 1

            prov = (meta.get("provenance") or "").lower()
            if prov == "observed" or src == "HAR":
                observed_count += 1
            elif prov == "imported" or src == "POSTMAN":
                imported_count += 1
            else:
                documented_count += 1

            has_desc = bool(meta.get("description"))
            has_params = bool(ep.parameters and len(ep.parameters) > 0)
            if not has_desc or not has_params:
                incomplete_count += 1

        inferred_rel_count = sum(1 for r in relationships if (r.provenance or "").lower() == "inferred")

        return {
            "total_endpoints": len(endpoints),
            "unique_resources": len(unique_resources),
            "method_distribution": method_dist,
            "category_distribution": category_dist,
            "source_distribution": source_dist,
            "documented_count": documented_count,
            "observed_count": observed_count,
            "imported_count": imported_count,
            "inferred_relationships_count": inferred_rel_count,
            "total_relationships_count": len(relationships),
            "unclassified_count": unclassified_count,
            "incomplete_metadata_count": incomplete_count,
        }

    @classmethod
    async def export_inventory(
        cls,
        db: AsyncSession,
        app_id: uuid.UUID,
        org_id: uuid.UUID,
        export_format: str = "json"
    ) -> Tuple[str, str]:
        """
        Exports the API inventory in JSON or CSV format.
        Sanitizes CSV fields against formula injection.
        """
        await cls.validate_app_ownership(db, app_id, org_id)

        result = await db.execute(
            select(DiscoveredEndpoint).where(DiscoveredEndpoint.application_id == app_id).order_by(DiscoveredEndpoint.path.asc())
        )
        endpoints = result.scalars().all()

        if export_format.lower() == "csv":
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow([
                "ID", "Method", "Path", "Resource", "Category", "Confidence",
                "Auth Required", "Parameters Count", "Response Codes", "Source", "Last Seen"
            ])

            for ep in endpoints:
                meta = ep.raw_metadata or {}
                method_str = ep.method.value if hasattr(ep.method, "value") else str(ep.method)

                # Formula injection prevention for CSV
                path_val = ep.path
                if path_val.startswith(("=", "+", "-", "@")):
                    path_val = "'" + path_val

                res_val = meta.get("resource_name", "")
                if res_val.startswith(("=", "+", "-", "@")):
                    res_val = "'" + res_val

                writer.writerow([
                    str(ep.id),
                    method_str,
                    path_val,
                    res_val,
                    meta.get("category", ApiCategory.UNCLASSIFIED),
                    meta.get("category_confidence", 0.0),
                    ep.auth_required,
                    len(ep.parameters or []),
                    ",".join(str(c) for c in (ep.response_codes or [])),
                    meta.get("discovery_source", "OPENAPI"),
                    meta.get("last_observed_at", ep.created_at.isoformat())
                ])

            return output.getvalue(), "text/csv"

        # Default JSON export
        export_data = []
        for ep in endpoints:
            method_str = ep.method.value if hasattr(ep.method, "value") else str(ep.method)
            meta = ep.raw_metadata or {}
            export_data.append({
                "id": str(ep.id),
                "application_id": str(ep.application_id),
                "path": ep.path,
                "method": method_str,
                "auth_required": ep.auth_required,
                "parameters": ep.parameters,
                "response_codes": ep.response_codes,
                "risk_level": ep.risk_level.value if hasattr(ep.risk_level, "value") else str(ep.risk_level),
                "resource": meta.get("resource_name"),
                "parent_resource": meta.get("parent_resource_name"),
                "category": meta.get("category", ApiCategory.UNCLASSIFIED),
                "category_confidence": meta.get("category_confidence", 0.0),
                "category_explanation": meta.get("category_explanation", ""),
                "category_provenance": meta.get("category_provenance", "rule-based"),
                "metadata": meta,
                "created_at": ep.created_at.isoformat(),
            })

        return json.dumps(export_data, indent=2), "application/json"
