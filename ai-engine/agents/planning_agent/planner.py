
from typing import Any, Dict, List
from pydantic import BaseModel, Field

from shared.enums.common import SafetyClassification, HttpMethod


class PlannedScenario(BaseModel):
    scenario_id: str
    name: str
    category: str
    target_endpoint: str
    method: str
    hypothesis: str
    safety_classification: SafetyClassification
    priority: int
    preconditions: List[str] = Field(default_factory=list)


class AutonomousTestPlanner:
    """Generate security test plans from discovered application behaviour."""

    MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
    VALID_METHODS = {method.value for method in HttpMethod}

    def generate_plan(
        self,
        endpoints: List[Dict[str, Any]],
        workflow_sequences: List[List[str]] = None,
        role_hierarchy: Dict[str, List[str]] = None
    ) -> List[PlannedScenario]:

        scenarios = []
        counter = 1
        workflow_sequences = workflow_sequences or []
        role_hierarchy = role_hierarchy or {}

        def add_scenario(name, category, path, method,
                         hypothesis, safety, priority, preconditions):
            nonlocal counter

            scenarios.append(
                PlannedScenario(
                    scenario_id=f"PLAN-{counter:03d}",
                    name=name,
                    category=category,
                    target_endpoint=path,
                    method=method,
                    hypothesis=hypothesis,
                    safety_classification=safety,
                    priority=priority,
                    preconditions=preconditions
                )
            )
            counter += 1

        endpoint_keys = set()

        for endpoint in endpoints:
            if not isinstance(endpoint, dict):
                continue

            path = str(endpoint.get("path") or "").strip()
            method = str(endpoint.get("method") or "GET").upper()

            if not path or method not in self.VALID_METHODS:
                continue

            endpoint_keys.add(f"{method}:{path}")

            roles = endpoint.get("required_roles") or []
            schemas = endpoint.get("input_schemas") or {}
            mutations = endpoint.get("state_mutations") or []
            authentication = endpoint.get("authentication") or {}

            auth_required = endpoint.get("auth_required")

            if auth_required is None:
                if isinstance(authentication, dict) and "auth_type" in authentication:
                    auth_required = (
                        str(authentication["auth_type"]).upper() != "NONE"
                    )
                else:
                    auth_required = bool(roles)

            mutating = method in self.MUTATING_METHODS

            endpoint_safety = (
                SafetyClassification.STATE_MODIFYING
                if mutating
                else SafetyClassification.SAFE_READ_ONLY
            )

            # Authentication testing
            if auth_required:
                add_scenario(
                    "Authentication Enforcement Check",
                    "AUTHENTICATION",
                    path,
                    method,
                    "Requests without valid authentication should be rejected.",
                    endpoint_safety,
                    1,
                    [
                        "Use an authorized test environment",
                        "Use approved synthetic accounts",
                        "Do not use real user credentials"
                    ]
                )

            # Role authorization testing
            if roles:
                add_scenario(
                    "Role Authorization Check",
                    "AUTHORIZATION",
                    path,
                    method,
                    "Users without the required role should not access restricted resources.",
                    endpoint_safety,
                    1,
                    [
                        "Use approved synthetic test accounts",
                        "Compare only authorized test roles",
                        "Do not access real users' resources"
                    ]
                )

            # Input validation testing
            if schemas:
                input_safety = (
                    SafetyClassification.STATE_MODIFYING
                    if mutating
                    else SafetyClassification.LOW_RISK_PROBE
                )

                add_scenario(
                    "Input Validation Check",
                    "INPUT_VALIDATION",
                    path,
                    method,
                    "Inputs should comply with the endpoint's declared schema.",
                    input_safety,
                    2,
                    [
                        "Use synthetic test data",
                        "Use non-destructive test inputs",
                        "Require approval for state-modifying tests"
                    ]
                )

            # Behavioral Digital Twin state mutation analysis
            if mutations:
                add_scenario(
                    "State Mutation Review",
                    "STATE_MUTATION",
                    path,
                    method,
                    f"Review whether expected state changes are restricted and valid: {mutations}",
                    SafetyClassification.STATE_MODIFYING,
                    1,
                    [
                        "Use isolated synthetic resources",
                        "Do not modify real user data",
                        "Require explicit execution approval"
                    ]
                )

        # Workflow sequence validation
        for workflow in workflow_sequences:
            missing = [
                key for key in workflow
                if key not in endpoint_keys
            ]

            if missing:
                add_scenario(
                    "Workflow Endpoint Consistency Review",
                    "WORKFLOW_VALIDATION",
                    missing[0].split(":", 1)[1],
                    missing[0].split(":", 1)[0],
                    f"Review workflow sequence for missing endpoints: {missing}",
                    SafetyClassification.SAFE_READ_ONLY,
                    2,
                    [
                        "Review discovered endpoint inventory",
                        "Treat missing endpoints as review findings",
                        "Do not execute workflow operations"
                    ]
                )

        return scenarios
