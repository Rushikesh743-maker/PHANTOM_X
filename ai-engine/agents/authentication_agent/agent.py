
from typing import Optional, Any

from agents.base import BaseAgent
from schemas.agent_io import AgentContext, AgentResult, AgentStatus
from llm.providers.base import LLMProvider


class AuthenticationAgent(BaseAgent):
    """
    Analyzes discovered authentication configurations,
    endpoint protection, and potential authentication weaknesses.

    Configuration analysis only. No authentication bypass attempts.
    """

    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        super().__init__(
            agent_name="AuthenticationAgent",
            llm_provider=llm_provider
        )

    async def _run(self, context: AgentContext) -> AgentResult:

        artifacts = context.discovered_artifacts or {}

        # 1. Obtain endpoint information
        endpoints = artifacts.get("endpoints")

        if not endpoints:
            twin = artifacts.get("behavioral_twin", {})

            if hasattr(twin, "model_dump"):
                twin = twin.model_dump()

            if isinstance(twin, dict):
                endpoints = twin.get("endpoints", [])

        if not endpoints:
            endpoints = context.parameters.get("endpoints", [])

        if isinstance(endpoints, dict):
            endpoints = list(endpoints.values())

        # 2. Normalize endpoint objects
        normalized_endpoints = []

        for endpoint in endpoints or []:
            if hasattr(endpoint, "model_dump"):
                endpoint = endpoint.model_dump()

            if isinstance(endpoint, dict):
                normalized_endpoints.append(endpoint)

        auth_mechanisms = set()
        findings = []
        analyzed_endpoints = []

        authenticated_count = 0
        unknown_auth_count = 0

        # 3. Analyze authentication configuration
        for endpoint in normalized_endpoints:

            path = str(endpoint.get("path", "UNKNOWN"))
            method = str(endpoint.get("method", "GET")).upper()

            authentication = endpoint.get("authentication") or {}

            if hasattr(authentication, "model_dump"):
                authentication = authentication.model_dump()

            if not isinstance(authentication, dict):
                authentication = {}

            auth_type = str(
                authentication.get("auth_type", "UNKNOWN")
            ).upper()

            roles = (
                authentication.get("roles_permitted")
                or endpoint.get("required_roles")
                or []
            )

            auth_required = endpoint.get("auth_required")

            # Infer authentication requirement only when possible.
            if auth_required is None:
                if auth_type not in ("UNKNOWN", "NONE"):
                    auth_required = True
                elif roles:
                    auth_required = True

            if auth_required is True:
                authenticated_count += 1

            if auth_required is None:
                unknown_auth_count += 1

            analyzed_endpoints.append({
                "path": path,
                "method": method,
                "auth_required": auth_required,
                "auth_type": auth_type,
                "roles_permitted": roles
            })

            if auth_type not in ("UNKNOWN", "NONE"):
                auth_mechanisms.add(auth_type)

            # 4. Check for potentially public endpoints
            if (
                auth_required is False
                and method not in ("OPTIONS", "HEAD")
            ):
                findings.append({
                    "finding_id": f"AUTH-{len(findings) + 1:03d}",
                    "type": "AUTHENTICATION_NOT_REQUIRED",
                    "endpoint": path,
                    "method": method,
                    "severity": "REVIEW",
                    "description": (
                        "Authentication is explicitly marked as not required. "
                        "Verify whether this endpoint is intentionally public."
                    )
                })

            # 5. Check missing authentication mechanism
            if (
                auth_required is True
                and auth_type in ("UNKNOWN", "NONE")
            ):
                findings.append({
                    "finding_id": f"AUTH-{len(findings) + 1:03d}",
                    "type": "AUTH_CONFIGURATION_MISSING",
                    "endpoint": path,
                    "method": method,
                    "severity": "HIGH",
                    "description": (
                        "Authentication is required, but no valid "
                        "authentication mechanism was discovered."
                    )
                })

            # 6. Check role configuration
            if auth_required is True and not roles:
                findings.append({
                    "finding_id": f"AUTH-{len(findings) + 1:03d}",
                    "type": "ROLE_CONFIGURATION_NOT_DISCOVERED",
                    "endpoint": path,
                    "method": method,
                    "severity": "REVIEW",
                    "description": (
                        "No permitted roles were discovered. "
                        "Review authorization configuration separately."
                    )
                })

        # 7. Return structured analysis
        mechanisms = sorted(auth_mechanisms)

        return AgentResult(
            agent_name=self.agent_name,
            status=AgentStatus.COMPLETED,
            output_data={
                "auth_mechanisms": mechanisms,
                "endpoints_analyzed": len(analyzed_endpoints),
                "authenticated_endpoints": authenticated_count,
                "unknown_authentication_endpoints": unknown_auth_count,
                "findings_count": len(findings),
                "analyzed_endpoints": analyzed_endpoints,
                "flaws_detected": findings,
                "token_entropy_assessment": "NOT_ASSESSED",
                "analysis_type": "STATIC_CONFIGURATION_ANALYSIS"
            },
            proposed_actions=[
                {
                    "action": "SUBMIT_AUTH_FINDINGS_FOR_REVIEW",
                    "findings_count": len(findings)
                }
            ],
            confidence=0.90 if analyzed_endpoints else 0.20
        )
