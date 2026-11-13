from typing import Dict, Any, List
from pydantic import BaseModel, Field


class EndpointBehavior(BaseModel):
    path: str
    method: str
    expected_status_codes: List[int]
    required_roles: List[str]
    input_schemas: Dict[str, Any] = Field(default_factory=dict)
    state_mutations: List[str] = Field(default_factory=list)


class BehavioralDigitalTwin(BaseModel):
    """In-memory behavioral model of the target application."""

    application_id: str
    endpoints: Dict[str, EndpointBehavior] = Field(default_factory=dict)
    role_hierarchy: Dict[str, List[str]] = Field(default_factory=dict)
    workflow_sequences: List[List[str]] = Field(default_factory=list)

    def register_endpoint(self, behavior: EndpointBehavior):
        key = f"{behavior.method.upper()}:{behavior.path}"
        self.endpoints[key] = behavior

    def get_mutating_endpoints(self) -> List[EndpointBehavior]:
        return [
            ep for ep in self.endpoints.values()
            if ep.method.upper() in ["POST", "PUT", "DELETE", "PATCH"]
            or bool(ep.state_mutations)
        ]

    def validate_workflows(self) -> Dict[str, Any]:
        """Check whether workflow steps reference registered endpoints."""
        results = []

        for index, workflow in enumerate(self.workflow_sequences, start=1):
            missing = [
                step for step in workflow
                if step not in self.endpoints
            ]

            results.append({
                "workflow_id": f"WORKFLOW-{index:03d}",
                "valid": len(missing) == 0,
                "missing_endpoints": missing
            })

        return {
            "workflows_checked": len(results),
            "valid_workflows": sum(r["valid"] for r in results),
            "invalid_workflows": sum(not r["valid"] for r in results),
            "results": results
        }

    def analyze_role_boundaries(self) -> List[Dict[str, Any]]:
        """Flag endpoints whose access roles need review."""
        findings = []

        for key, endpoint in self.endpoints.items():
            if not endpoint.required_roles:
                findings.append({
                    "endpoint": key,
                    "finding": "NO_REQUIRED_ROLE_DEFINED",
                    "severity": "REVIEW",
                    "description": (
                        "No required role is documented. "
                        "Verify whether public access is intentional."
                    )
                })

        return findings

    def analyze_state_mutations(self) -> List[Dict[str, Any]]:
        """Describe endpoints that may change application state."""
        results = []

        for key, endpoint in self.endpoints.items():
            if endpoint in self.get_mutating_endpoints():
                results.append({
                    "endpoint": key,
                    "state_mutations": endpoint.state_mutations,
                    "requires_execution_review": True
                })

        return results