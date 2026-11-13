
from typing import Optional, Any, Dict, List

from agents.base import BaseAgent
from schemas.agent_io import AgentContext, AgentResult, AgentStatus
from llm.providers.base import LLMProvider


class AuthorizationAgent(BaseAgent):
    """
    Analyzes endpoint authorization metadata.

    Reviews role restrictions, object-level access,
    tenant isolation and privileged endpoint boundaries.

    Static analysis only. Does not execute requests.
    """

    OBJECT_ID_FIELDS = {
        "id",
        "user_id",
        "account_id",
        "project_id",
        "order_id",
        "resource_id",
        "document_id",
        "record_id",
    }

    PRIVILEGED_ROLES = {
        "ADMIN",
        "SUPER_ADMIN",
        "OWNER",
    }

    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        super().__init__(
            agent_name="AuthorizationAgent",
            llm_provider=llm_provider
        )

    async def _run(self, context: AgentContext) -> AgentResult:

        artifacts = context.discovered_artifacts or {}

        # 1. Obtain endpoint information
        endpoints = artifacts.get("endpoints")

        twin = artifacts.get("behavioral_twin", {})

        if hasattr(twin, "model_dump"):
            twin = twin.model_dump()

        if not endpoints and isinstance(twin, dict):
            endpoints = twin.get("endpoints", [])

        if not endpoints:
            endpoints = context.parameters.get("endpoints", [])

        if isinstance(endpoints, dict):
            endpoints = list(endpoints.values())

        # 2. Normalize endpoint data
        normalized_endpoints = []

        for endpoint in endpoints or []:

            if hasattr(endpoint, "model_dump"):
                endpoint = endpoint.model_dump()

            if isinstance(endpoint, dict):
                normalized_endpoints.append(endpoint)

        findings: List[Dict[str, Any]] = []
        cross_tenant_matrix: List[Dict[str, Any]] = []
        risk_areas = []

        def add_finding(
            endpoint_path: str,
            method: str,
            finding_type: str,
            severity: str,
            description: str,
            recommended_check: Optional[str] = None
        ):
            finding = {
                "finding_id": f"AUTHZ-{len(findings) + 1:03d}",
                "type": finding_type,
                "endpoint": endpoint_path,
                "method": method,
                "severity": severity,
                "description": description,
            }

            if recommended_check:
                finding["recommended_check"] = recommended_check

            findings.append(finding)

        # 3. Analyze every endpoint
        for endpoint in normalized_endpoints:

            path = str(endpoint.get("path", "")).strip()

            if not path:
                continue

            method = str(
                endpoint.get("method", "GET")
            ).upper()

            authentication = endpoint.get("authentication") or {}

            if hasattr(authentication, "model_dump"):
                authentication = authentication.model_dump()

            if not isinstance(authentication, dict):
                authentication = {}

            # Read roles from both supported metadata locations
            required_roles = (
                endpoint.get("required_roles")
                or authentication.get("roles_permitted")
                or []
            )

            if isinstance(required_roles, str):
                required_roles = [required_roles]

            required_roles = [
                str(role).upper()
                for role in required_roles
                if role
            ]

            # Determine authentication requirement
            auth_required = endpoint.get("auth_required")

            if auth_required is None:
                auth_type = str(
                    authentication.get("auth_type", "UNKNOWN")
                ).upper()

                if auth_type not in ("UNKNOWN", "NONE"):
                    auth_required = True
                elif required_roles:
                    auth_required = True

            # Normalize endpoint parameters
            parameters = endpoint.get("parameters") or []
            input_schemas = endpoint.get("input_schemas") or {}

            parameter_names = []

            if isinstance(parameters, dict):
                parameter_names.extend(parameters.keys())

            elif isinstance(parameters, list):
                for parameter in parameters:
                    if isinstance(parameter, dict):
                        name = parameter.get("name")
                        if name:
                            parameter_names.append(name)

            if isinstance(input_schemas, dict):
                parameter_names.extend(input_schemas.keys())

            parameter_names = {
                str(name).lower()
                for name in parameter_names
                if name
            }

            path_lower = path.lower()

            # 4. Missing authentication metadata
            if auth_required is False and method not in ("OPTIONS", "HEAD"):

                add_finding(
                    path,
                    method,
                    "AUTHENTICATION_NOT_REQUIRED",
                    "REVIEW",
                    "Authentication is explicitly marked as not required. "
                    "Verify whether this endpoint is intentionally public."
                )

            elif auth_required is None:

                add_finding(
                    path,
                    method,
                    "AUTHENTICATION_REQUIREMENT_UNKNOWN",
                    "REVIEW",
                    "Authentication requirements could not be determined "
                    "from the discovered endpoint metadata."
                )

            # 5. Missing role restrictions
            if auth_required is True and not required_roles:

                add_finding(
                    path,
                    method,
                    "ROLE_RESTRICTION_NOT_DEFINED",
                    "REVIEW",
                    "The endpoint requires authentication, but permitted "
                    "roles were not discovered. Review its authorization policy."
                )

            # 6. Object-level authorization review
            has_object_identifier = (
                ("{" in path and "}" in path)
                or bool(parameter_names & self.OBJECT_ID_FIELDS)
            )

            if has_object_identifier and auth_required is True:

                add_finding(
                    path,
                    method,
                    "OBJECT_LEVEL_AUTHORIZATION_REVIEW",
                    "REVIEW",
                    "The endpoint references an individual object. "
                    "Verify that users can access only authorized resources.",
                    "Compare access using approved synthetic accounts "
                    "and isolated test resources."
                )

                risk_areas.append(
                    f"Object-level authorization: {path}"
                )

            # 7. Tenant isolation review
            has_tenant_reference = (
                "tenant" in path_lower
                or any(
                    "tenant" in name
                    for name in parameter_names
                )
            )

            if has_tenant_reference:

                cross_tenant_matrix.append({
                    "endpoint": path,
                    "method": method,
                    "check": "TENANT_ISOLATION",
                    "expected_behavior": (
                        "A tenant must access only its own authorized resources."
                    ),
                    "test_accounts": [
                        "synthetic_tenant_A",
                        "synthetic_tenant_B"
                    ]
                })

                add_finding(
                    path,
                    method,
                    "TENANT_ISOLATION_REVIEW",
                    "REVIEW",
                    "Tenant-related information was discovered. "
                    "Verify that tenant boundaries are enforced.",
                    "Compare access using isolated synthetic tenants."
                )

                risk_areas.append(
                    f"Tenant isolation: {path}"
                )

            # 8. Privileged role boundary review
            if any(
                role in self.PRIVILEGED_ROLES
                for role in required_roles
            ):

                add_finding(
                    path,
                    method,
                    "PRIVILEGED_ENDPOINT_REVIEW",
                    "REVIEW",
                    "The endpoint permits a privileged role. "
                    "Verify that lower-privileged users cannot perform "
                    "the same restricted operation.",
                    "Compare permissions using approved synthetic "
                    "ADMIN and USER accounts."
                )

                risk_areas.append(
                    f"Vertical privilege boundary: {path}"
                )

        # 9. Build final result
        return AgentResult(
            agent_name=self.agent_name,
            status=AgentStatus.COMPLETED,
            output_data={
                "endpoints_analyzed": len(normalized_endpoints),
                "findings_count": len(findings),
                "findings": findings,
                "cross_tenant_matrix": cross_tenant_matrix,
                "risk_areas": sorted(set(risk_areas)),
                "analysis_type": (
                    "STATIC_AUTHORIZATION_METADATA_ANALYSIS"
                ),
                "execution_note": (
                    "Findings are review hypotheses, not confirmed vulnerabilities."
                )
            },
            proposed_actions=[
                {
                    "action": "SUBMIT_AUTHORIZATION_FINDINGS_FOR_REVIEW",
                    "findings_count": len(findings)
                }
            ],
            confidence=0.90 if normalized_endpoints else 0.20
        )
