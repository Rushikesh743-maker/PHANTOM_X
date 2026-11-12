import uuid
import logging
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Tuple
from urllib.parse import urlparse

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc, delete
from fastapi import HTTPException, status

from app.models.application import Application
from app.models.scope_safety import ApplicationScopePolicy
from app.models.endpoint import DiscoveredEndpoint, DiscoveryJob
from app.services.application_service import ApplicationService
from app.features.security_operations.audit_logs.event_recorder import AuditEventRecorder
from app.features.security_operations.audit_logs.schemas import AuditEventType, AuditSeverity, AuditStatus
from app.discovery import (
    EndpointNormalizer,
    ScopeFilter,
    OpenApiParser,
    PostmanParser,
    HarDiscoveryParser
)
from shared.enums.common import HttpMethod, EndpointRiskLevel

logger = logging.getLogger("phantom_x.discovery_service")


class DiscoveryService:
    """
    Core service orchestrating API Endpoint Discovery across OpenAPI,
    Postman, HAR traffic, and passive observations with strict scope enforcement.
    """

    @classmethod
    async def validate_app_and_scope(
        cls,
        db: AsyncSession,
        app_id: uuid.UUID,
        org_id: uuid.UUID
    ) -> Tuple[Application, ApplicationScopePolicy]:
        """
        Validates target application existence, tenant ownership,
        scope policy existence, and active authorization validity.
        Fails safely if any requirement is not met.
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
                detail="Application not found"
            )

        scope_result = await db.execute(
            select(ApplicationScopePolicy).where(
                and_(
                    ApplicationScopePolicy.application_id == app_id,
                    ApplicationScopePolicy.organization_id == org_id
                )
            )
        )
        scope = scope_result.scalars().first()
        if not scope:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Application testing scope policy is missing. Register and configure testing scope before discovery."
            )

        # Dynamic expiry resolution
        scope_status, auth_status = ApplicationService._resolve_scope_status(scope)

        if auth_status != "AUTHORIZED" or scope_status != "ACTIVE":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Discovery blocked: Testing authorization is '{auth_status}' and scope status is '{scope_status}'. "
                    "An ACTIVE, non-expired authorization is strictly required to execute discovery."
                )
            )

        return app, scope

    @classmethod
    async def process_and_persist_endpoints(
        cls,
        db: AsyncSession,
        app: Application,
        scope: ApplicationScopePolicy,
        candidate_endpoints: List[Dict[str, Any]],
        source_type: str,
        user_id: Optional[uuid.UUID] = None
    ) -> Tuple[DiscoveryJob, List[DiscoveredEndpoint], List[Dict[str, Any]]]:
        """
        Evaluates extracted endpoints against scope policy, persists in-scope
        endpoints with deduplication, updates discovery job, and emits audit logs.
        """
        now = datetime.now(timezone.utc)
        job = DiscoveryJob(
            organization_id=app.organization_id,
            application_id=app.id,
            source_type=source_type,
            status="RUNNING",
            endpoints_found=len(candidate_endpoints),
            endpoints_in_scope=0,
            endpoints_out_of_scope=0,
            summary={},
            started_at=now
        )
        db.add(job)
        await db.flush()

        if not candidate_endpoints:
            job.status = "FAILED"
            job.error_message = "No endpoints could be extracted from the provided source."
            job.completed_at = datetime.now(timezone.utc)
            await db.commit()
            await db.refresh(job)
            return job, [], []

        # Scope enforcement
        in_scope, out_of_scope = ScopeFilter.evaluate_endpoints(candidate_endpoints, scope)
        job.endpoints_in_scope = len(in_scope)
        job.endpoints_out_of_scope = len(out_of_scope)

        if not in_scope and candidate_endpoints:
            # All candidates were rejected by scope
            job.status = "FAILED"
            job.error_message = f"All {len(candidate_endpoints)} extracted endpoints were out of authorized scope."
            job.summary = {
                "total_candidates": len(candidate_endpoints),
                "out_of_scope_reasons": out_of_scope
            }
            job.completed_at = datetime.now(timezone.utc)
            await db.commit()
            await db.refresh(job)
            return job, [], out_of_scope

        persisted_endpoints: List[DiscoveredEndpoint] = []

        for ep_data in in_scope:
            method_str = ep_data.get("method", "GET").upper()
            path_str = ep_data.get("path", "/")

            # Convert to HttpMethod enum
            try:
                http_method = HttpMethod(method_str)
            except ValueError:
                http_method = HttpMethod.GET

            # Deduplication check against existing endpoints
            existing_result = await db.execute(
                select(DiscoveredEndpoint).where(
                    and_(
                        DiscoveredEndpoint.application_id == app.id,
                        DiscoveredEndpoint.path == path_str,
                        DiscoveredEndpoint.method == http_method
                    )
                )
            )
            existing_ep = existing_result.scalars().first()

            if existing_ep:
                # Merge parameters
                existing_param_keys = {(p.get("name"), p.get("location")) for p in existing_ep.parameters}
                new_params = list(existing_ep.parameters)
                for p in ep_data.get("parameters", []):
                    if (p.get("name"), p.get("location")) not in existing_param_keys:
                        new_params.append(p)
                existing_ep.parameters = new_params

                # Merge response status codes
                merged_codes = sorted(list(set(existing_ep.response_codes + ep_data.get("response_codes", []))))
                existing_ep.response_codes = merged_codes

                # Merge raw metadata
                current_meta = dict(existing_ep.raw_metadata or {})
                new_meta = ep_data.get("raw_metadata", {})
                current_meta["last_observed_at"] = now.isoformat()
                current_meta["discovery_sources"] = list(set(
                    current_meta.get("discovery_sources", [current_meta.get("discovery_source", source_type)]) + [source_type]
                ))
                if new_meta.get("request_body_schema"):
                    current_meta["request_body_schema"] = new_meta["request_body_schema"]
                if new_meta.get("response_schemas"):
                    current_meta.setdefault("response_schemas", {}).update(new_meta["response_schemas"])

                existing_ep.raw_metadata = current_meta
                persisted_endpoints.append(existing_ep)
            else:
                # Create new endpoint record
                raw_meta = dict(ep_data.get("raw_metadata", {}))
                raw_meta["discovery_source"] = source_type
                raw_meta["discovery_sources"] = [source_type]
                raw_meta["first_discovered_at"] = now.isoformat()
                raw_meta["last_observed_at"] = now.isoformat()

                new_ep = DiscoveredEndpoint(
                    application_id=app.id,
                    path=path_str,
                    method=http_method,
                    auth_required=ep_data.get("auth_required", True),
                    parameters=ep_data.get("parameters", []),
                    response_codes=ep_data.get("response_codes", [200]),
                    risk_level=EndpointRiskLevel.UNASSESSED,
                    raw_metadata=raw_meta
                )
                db.add(new_ep)
                persisted_endpoints.append(new_ep)

        # Classify and tag all persisted endpoints
        from app.services.inventory_service import InventoryService
        for ep in persisted_endpoints:
            InventoryService.classify_and_tag_endpoint(ep)

        job.status = "COMPLETED"
        job.completed_at = datetime.now(timezone.utc)
        job.summary = {
            "total_candidates": len(candidate_endpoints),
            "in_scope_persisted": len(persisted_endpoints),
            "out_of_scope_count": len(out_of_scope),
            "out_of_scope_reasons": out_of_scope[:20]
        }
        await db.commit()

        # Rebuild relationship mappings in the background of discovery completion
        try:
            await InventoryService.rebuild_inventory_mappings(db, app.id, app.organization_id)
        except Exception as e:
            logger.warning(f"Failed to auto-rebuild inventory relationships: {e}")

        # Structured audit recording
        try:
            await AuditEventRecorder.record_application_event(
                db=db,
                org_id=app.organization_id,
                app_id=app.id,
                event_type="DISCOVERY_COMPLETED",
                action="ENDPOINT_DISCOVERY",
                details={
                    "source_type": source_type,
                    "endpoints_found": len(candidate_endpoints),
                    "endpoints_persisted": len(persisted_endpoints),
                    "endpoints_rejected_scope": len(out_of_scope)
                }
            )
        except Exception as audit_err:
            logger.warning(f"Audit log recording skipped: {audit_err}")

        await db.commit()
        await db.refresh(job)
        return job, persisted_endpoints, out_of_scope

    @classmethod
    async def import_openapi(
        cls,
        db: AsyncSession,
        app_id: uuid.UUID,
        org_id: uuid.UUID,
        content: str,
        user_id: Optional[uuid.UUID] = None
    ) -> Tuple[DiscoveryJob, List[DiscoveredEndpoint], List[Dict[str, Any]]]:
        """Imports and analyzes an OpenAPI / Swagger specification."""
        app, scope = await cls.validate_app_and_scope(db, app_id, org_id)

        try:
            candidates = OpenApiParser.parse_specification(content, default_base_url=app.target_url)
        except ValueError as ve:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(ve)
            )

        return await cls.process_and_persist_endpoints(
            db=db,
            app=app,
            scope=scope,
            candidate_endpoints=candidates,
            source_type="OPENAPI",
            user_id=user_id
        )

    @classmethod
    async def import_postman(
        cls,
        db: AsyncSession,
        app_id: uuid.UUID,
        org_id: uuid.UUID,
        content: str,
        user_id: Optional[uuid.UUID] = None
    ) -> Tuple[DiscoveryJob, List[DiscoveredEndpoint], List[Dict[str, Any]]]:
        """Imports and analyzes a Postman collection."""
        app, scope = await cls.validate_app_and_scope(db, app_id, org_id)

        try:
            candidates = PostmanParser.parse_collection(content, default_base_url=app.target_url)
        except ValueError as ve:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(ve)
            )

        return await cls.process_and_persist_endpoints(
            db=db,
            app=app,
            scope=scope,
            candidate_endpoints=candidates,
            source_type="POSTMAN",
            user_id=user_id
        )

    @classmethod
    async def import_har(
        cls,
        db: AsyncSession,
        app_id: uuid.UUID,
        org_id: uuid.UUID,
        content: str,
        user_id: Optional[uuid.UUID] = None
    ) -> Tuple[DiscoveryJob, List[DiscoveredEndpoint], List[Dict[str, Any]]]:
        """Imports and analyzes HTTP Archive (.har) recorded traffic."""
        app, scope = await cls.validate_app_and_scope(db, app_id, org_id)

        try:
            candidates = HarDiscoveryParser.parse_har_log(content, default_base_url=app.target_url)
        except ValueError as ve:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(ve)
            )

        return await cls.process_and_persist_endpoints(
            db=db,
            app=app,
            scope=scope,
            candidate_endpoints=candidates,
            source_type="HAR",
            user_id=user_id
        )

    @classmethod
    async def trigger_discovery(
        cls,
        db: AsyncSession,
        app_id: uuid.UUID,
        org_id: uuid.UUID,
        source_type: str = "SPECIFICATION",
        spec_content: Optional[str] = None,
        user_id: Optional[uuid.UUID] = None
    ) -> Tuple[DiscoveryJob, List[DiscoveredEndpoint], List[Dict[str, Any]]]:
        """
        Triggers discovery for an authorized target application.
        Dispatches to specification parsers if provided, or profiles registered target boundaries.
        """
        app, scope = await cls.validate_app_and_scope(db, app_id, org_id)

        candidates: List[Dict[str, Any]] = []

        if spec_content:
            st = source_type.upper()
            if "POSTMAN" in st:
                return await cls.import_postman(db, app_id, org_id, spec_content, user_id)
            elif "HAR" in st:
                return await cls.import_har(db, app_id, org_id, spec_content, user_id)
            else:
                return await cls.import_openapi(db, app_id, org_id, spec_content, user_id)
        else:
            # Profile default target boundary routes from environment
            base_url = app.target_url.rstrip("/")
            now_iso = datetime.now(timezone.utc).isoformat()
            default_paths = ["/health", "/api/v1", "/api"]
            for dp in default_paths:
                candidates.append({
                    "path": dp,
                    "method": "GET",
                    "auth_required": False,
                    "parameters": [],
                    "response_codes": [200],
                    "risk_level": "UNASSESSED",
                    "raw_metadata": {
                        "base_url": base_url,
                        "original_path": dp,
                        "discovery_source": "PASSIVE",
                        "evidence_classification": "OBSERVED",
                        "first_discovered_at": now_iso,
                        "last_observed_at": now_iso,
                    }
                })

        return await cls.process_and_persist_endpoints(
            db=db,
            app=app,
            scope=scope,
            candidate_endpoints=candidates,
            source_type=source_type.upper(),
            user_id=user_id
        )

    @classmethod
    async def list_endpoints(
        cls,
        db: AsyncSession,
        org_id: uuid.UUID,
        app_id: Optional[uuid.UUID] = None,
        method: Optional[str] = None,
        path: Optional[str] = None,
        search: Optional[str] = None,
        risk_level: Optional[str] = None,
        source: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[DiscoveredEndpoint]:
        """
        Lists discovered endpoints strictly filtered by caller organization,
        with optional application, method, path, search, and source filtering.
        """
        query = (
            select(DiscoveredEndpoint)
            .join(Application, DiscoveredEndpoint.application_id == Application.id)
            .where(Application.organization_id == org_id)
        )

        if app_id:
            query = query.where(DiscoveredEndpoint.application_id == app_id)

        if method:
            try:
                http_m = HttpMethod(method.upper().strip())
                query = query.where(DiscoveredEndpoint.method == http_m)
            except ValueError:
                pass

        if path:
            query = query.where(DiscoveredEndpoint.path.ilike(f"%{path.strip()}%"))

        if search:
            s = f"%{search.strip()}%"
            query = query.where(
                or_(
                    DiscoveredEndpoint.path.ilike(s),
                    Application.name.ilike(s)
                )
            )

        if risk_level:
            try:
                r_level = EndpointRiskLevel(risk_level.upper().strip())
                query = query.where(DiscoveredEndpoint.risk_level == r_level)
            except ValueError:
                pass

        query = query.order_by(desc(DiscoveredEndpoint.created_at)).offset(skip).limit(limit)
        result = await db.execute(query)
        endpoints = result.scalars().all()

        if source:
            source_upper = source.upper().strip()
            endpoints = [
                ep for ep in endpoints
                if ep.raw_metadata and (
                    ep.raw_metadata.get("discovery_source") == source_upper
                    or source_upper in ep.raw_metadata.get("discovery_sources", [])
                )
            ]

        return endpoints

    @classmethod
    async def get_endpoint(
        cls,
        db: AsyncSession,
        endpoint_id: uuid.UUID,
        org_id: uuid.UUID
    ) -> DiscoveredEndpoint:
        """Retrieves a single discovered endpoint ensuring tenant isolation."""
        query = (
            select(DiscoveredEndpoint)
            .join(Application, DiscoveredEndpoint.application_id == Application.id)
            .where(
                and_(
                    DiscoveredEndpoint.id == endpoint_id,
                    Application.organization_id == org_id
                )
            )
        )
        result = await db.execute(query)
        ep = result.scalars().first()
        if not ep:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Endpoint not found"
            )
        return ep

    @classmethod
    async def delete_endpoint(
        cls,
        db: AsyncSession,
        endpoint_id: uuid.UUID,
        org_id: uuid.UUID
    ) -> None:
        """Deletes a discovered endpoint ensuring tenant isolation."""
        ep = await cls.get_endpoint(db, endpoint_id, org_id)
        await db.delete(ep)
        await db.commit()

    @classmethod
    async def list_jobs(
        cls,
        db: AsyncSession,
        org_id: uuid.UUID,
        app_id: Optional[uuid.UUID] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[DiscoveryJob]:
        """Lists discovery jobs for the organization."""
        query = select(DiscoveryJob).where(DiscoveryJob.organization_id == org_id)
        if app_id:
            query = query.where(DiscoveryJob.application_id == app_id)
        query = query.order_by(desc(DiscoveryJob.created_at)).offset(skip).limit(limit)
        result = await db.execute(query)
        return result.scalars().all()

    @classmethod
    async def get_job(
        cls,
        db: AsyncSession,
        job_id: uuid.UUID,
        org_id: uuid.UUID
    ) -> DiscoveryJob:
        """Retrieves a single discovery job ensuring tenant isolation."""
        result = await db.execute(
            select(DiscoveryJob).where(
                and_(
                    DiscoveryJob.id == job_id,
                    DiscoveryJob.organization_id == org_id
                )
            )
        )
        job = result.scalars().first()
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Discovery job not found"
            )
        return job

    @classmethod
    async def cancel_job(
        cls,
        db: AsyncSession,
        job_id: uuid.UUID,
        org_id: uuid.UUID
    ) -> DiscoveryJob:
        """Cancels a pending or running discovery job."""
        job = await cls.get_job(db, job_id, org_id)
        if job.status in ("PENDING", "RUNNING"):
            job.status = "CANCELLED"
            job.completed_at = datetime.now(timezone.utc)
            await db.commit()
            await db.refresh(job)
        return job

