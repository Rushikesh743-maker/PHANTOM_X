import uuid
from typing import List, Dict, Any, Optional, Set, Tuple
from .classifier import ApiCategory
from .resource_mapper import ResourceMapper


GENERIC_PARAM_NAMES = {
    "page", "limit", "skip", "offset", "count", "sort", "sort_by",
    "order", "order_by", "search", "q", "query", "filter", "fields",
    "format", "lang", "locale", "version", "api_key", "key"
}


class RelationshipType:
    SAME_RESOURCE = "SAME_RESOURCE"
    PARENT_CHILD = "PARENT_CHILD"
    READ_WRITE = "READ_WRITE"
    AUTH_DEPENDENCY = "AUTH_DEPENDENCY"
    SHARED_PARAMETER = "SHARED_PARAMETER"
    SHARED_SCHEMA = "SHARED_SCHEMA"
    WORKFLOW_CANDIDATE = "WORKFLOW_CANDIDATE"


class RelationshipProvenance:
    OBSERVED = "OBSERVED"
    DOCUMENTED = "DOCUMENTED"
    INFERRED = "INFERRED"


class RelationshipBuilder:
    """
    Infers and maps relationships and dependencies across discovered API endpoints.
    Explicitly tags evidence source, confidence score, and provenance level.
    """

    @classmethod
    def build_relationships(
        cls,
        endpoints: List[Dict[str, Any]],
        application_id: Optional[uuid.UUID] = None
    ) -> List[Dict[str, Any]]:
        """
        Analyzes a list of endpoint dictionaries and returns deduplicated relationships.
        """
        relationships: List[Dict[str, Any]] = []
        seen_keys: Set[Tuple[str, str, str]] = set()

        # Pre-process endpoints with resources and classification
        processed_endpoints = []
        auth_endpoints = []

        for ep in endpoints:
            ep_id = str(ep.get("id", ""))
            if not ep_id:
                continue

            path = ep.get("path", "/")
            method = ep.get("method", "GET").upper()
            auth_required = ep.get("auth_required", True)
            params = ep.get("parameters", [])
            raw_meta = ep.get("raw_metadata", {})
            source = ep.get("source", "openapi")

            res_name, parent_res, res_conf, res_ev = ResourceMapper.extract_resource(path)
            category = raw_meta.get("category", ApiCategory.UNCLASSIFIED)

            item = {
                "id": ep_id,
                "path": path,
                "method": method,
                "auth_required": auth_required,
                "parameters": params,
                "raw_metadata": raw_meta,
                "source": source,
                "resource_name": res_name,
                "parent_resource": parent_res,
                "category": category,
            }
            processed_endpoints.append(item)

            # Check if this is an authentication provider endpoint
            is_auth = (
                category == ApiCategory.AUTH_IDENTITY or
                any(k in path.lower() for k in ["/auth/login", "/auth/token", "/oauth/token", "/login"])
            ) and method in ("POST", "GET")
            if is_auth:
                auth_endpoints.append(item)

        # 1. Map Authentication Dependencies
        for auth_ep in auth_endpoints:
            for target_ep in processed_endpoints:
                if auth_ep["id"] == target_ep["id"]:
                    continue
                if (target_ep["auth_required"] or target_ep["category"] != ApiCategory.AUTH_IDENTITY) and target_ep["id"] not in [a["id"] for a in auth_endpoints]:
                    key = (auth_ep["id"], target_ep["id"], RelationshipType.AUTH_DEPENDENCY)
                    if key not in seen_keys:
                        seen_keys.add(key)
                        relationships.append({
                            "application_id": application_id,
                            "source_endpoint_id": auth_ep["id"],
                            "target_endpoint_id": target_ep["id"],
                            "relationship_type": RelationshipType.AUTH_DEPENDENCY,
                            "evidence_source": "auth_requirement",
                            "confidence": 0.85,
                            "explanation": f"Authenticated endpoint '{target_ep['path']}' requires token from '{auth_ep['path']}'",
                            "provenance": (
                                RelationshipProvenance.DOCUMENTED
                                if auth_ep["source"] == "openapi" and target_ep["source"] == "openapi"
                                else RelationshipProvenance.INFERRED
                            ),
                            "raw_metadata": {"auth_endpoint": auth_ep["path"]}
                        })

        # 2. Pairwise relationships (Same-Resource, Parent-Child, Read-Write, Shared-Param, Shared-Schema, Workflow)
        for i in range(len(processed_endpoints)):
            ep_a = processed_endpoints[i]
            for j in range(len(processed_endpoints)):
                if i == j:
                    continue
                ep_b = processed_endpoints[j]

                # A. Same Resource
                if ep_a["resource_name"] == ep_b["resource_name"] and ep_a["resource_name"] != "root":
                    key = (ep_a["id"], ep_b["id"], RelationshipType.SAME_RESOURCE)
                    if key not in seen_keys:
                        seen_keys.add(key)
                        relationships.append({
                            "application_id": application_id,
                            "source_endpoint_id": ep_a["id"],
                            "target_endpoint_id": ep_b["id"],
                            "relationship_type": RelationshipType.SAME_RESOURCE,
                            "evidence_source": "path_hierarchy",
                            "confidence": 0.95,
                            "explanation": f"Both endpoints operate on resource '{ep_a['resource_name']}'",
                            "provenance": (
                                RelationshipProvenance.DOCUMENTED
                                if ep_a["source"] == "openapi" and ep_b["source"] == "openapi"
                                else RelationshipProvenance.INFERRED
                            ),
                            "raw_metadata": {"resource": ep_a["resource_name"]}
                        })

                    # B. Read / Write Relationship (Create/Update -> Read)
                    if ep_a["method"] in ("POST", "PUT", "PATCH") and ep_b["method"] == "GET":
                        key_rw = (ep_a["id"], ep_b["id"], RelationshipType.READ_WRITE)
                        if key_rw not in seen_keys:
                            seen_keys.add(key_rw)
                            relationships.append({
                                "application_id": application_id,
                                "source_endpoint_id": ep_a["id"],
                                "target_endpoint_id": ep_b["id"],
                                "relationship_type": RelationshipType.READ_WRITE,
                                "evidence_source": "path_hierarchy",
                                "confidence": 0.85,
                                "explanation": f"Mutation '{ep_a['method']} {ep_a['path']}' precedes retrieval '{ep_b['method']} {ep_b['path']}'",
                                "provenance": RelationshipProvenance.INFERRED,  # Inferred unless traffic sequence proves it
                                "raw_metadata": {"mutation_method": ep_a["method"]}
                            })

                    # C. Workflow Lifecycle Candidate (POST create -> GET read -> PUT update -> DELETE delete)
                    lifecycle_pairs = [("POST", "GET"), ("GET", "PUT"), ("GET", "PATCH"), ("PUT", "DELETE"), ("PATCH", "DELETE")]
                    if (ep_a["method"], ep_b["method"]) in lifecycle_pairs:
                        key_wf = (ep_a["id"], ep_b["id"], RelationshipType.WORKFLOW_CANDIDATE)
                        if key_wf not in seen_keys:
                            seen_keys.add(key_wf)
                            relationships.append({
                                "application_id": application_id,
                                "source_endpoint_id": ep_a["id"],
                                "target_endpoint_id": ep_b["id"],
                                "relationship_type": RelationshipType.WORKFLOW_CANDIDATE,
                                "evidence_source": "crud_lifecycle",
                                "confidence": 0.80,
                                "explanation": f"Inferred CRUD lifecycle transition from {ep_a['method']} to {ep_b['method']}",
                                "provenance": RelationshipProvenance.INFERRED,
                                "raw_metadata": {"stage_a": ep_a["method"], "stage_b": ep_b["method"]}
                            })

                # D. Parent - Child Hierarchy
                if ep_b["parent_resource"] and ep_b["parent_resource"] == ep_a["resource_name"]:
                    key_pc = (ep_a["id"], ep_b["id"], RelationshipType.PARENT_CHILD)
                    if key_pc not in seen_keys:
                        seen_keys.add(key_pc)
                        relationships.append({
                            "application_id": application_id,
                            "source_endpoint_id": ep_a["id"],
                            "target_endpoint_id": ep_b["id"],
                            "relationship_type": RelationshipType.PARENT_CHILD,
                            "evidence_source": "path_hierarchy",
                            "confidence": 0.90,
                            "explanation": f"Child resource '{ep_b['resource_name']}' is nested under parent resource '{ep_a['resource_name']}'",
                            "provenance": (
                                RelationshipProvenance.DOCUMENTED
                                if ep_a["source"] == "openapi" and ep_b["source"] == "openapi"
                                else RelationshipProvenance.INFERRED
                            ),
                            "raw_metadata": {"parent": ep_a["resource_name"], "child": ep_b["resource_name"]}
                        })

                # E. Shared Non-Trivial Parameter Relationship
                params_a = {
                    p.get("name", "").lower()
                    for p in ep_a.get("parameters", [])
                    if p.get("name") and p.get("name").lower() not in GENERIC_PARAM_NAMES
                }
                params_b = {
                    p.get("name", "").lower()
                    for p in ep_b.get("parameters", [])
                    if p.get("name") and p.get("name").lower() not in GENERIC_PARAM_NAMES
                }
                shared_params = params_a.intersection(params_b)
                if shared_params:
                    # Pick most specific identifier parameter
                    param_name = sorted(list(shared_params))[0]
                    key_sp = (ep_a["id"], ep_b["id"], RelationshipType.SHARED_PARAMETER)
                    if key_sp not in seen_keys:
                        seen_keys.add(key_sp)
                        relationships.append({
                            "application_id": application_id,
                            "source_endpoint_id": ep_a["id"],
                            "target_endpoint_id": ep_b["id"],
                            "relationship_type": RelationshipType.SHARED_PARAMETER,
                            "evidence_source": "parameter_match",
                            "confidence": 0.80,
                            "explanation": f"Both endpoints consume entity parameter '{param_name}'",
                            "provenance": (
                                RelationshipProvenance.DOCUMENTED
                                if ep_a["source"] == "openapi" and ep_b["source"] == "openapi"
                                else RelationshipProvenance.INFERRED
                            ),
                            "raw_metadata": {"shared_parameters": list(shared_params)}
                        })

        return relationships
