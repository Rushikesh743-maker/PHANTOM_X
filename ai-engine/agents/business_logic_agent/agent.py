
from typing import Optional, Any, Dict, List
import re

from agents.base import BaseAgent
from schemas.agent_io import AgentContext, AgentResult, AgentStatus
from llm.providers.base import LLMProvider
from shared.enums.common import SafetyClassification


class BusinessLogicAgent(BaseAgent):
    """
    Analyzes application workflows and generates business logic
    security scenarios from discovered endpoint metadata.

    Static analysis only. Does not execute application requests.
    """

    MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

    WORKFLOW_KEYWORDS = {
        "checkout": "Checkout Workflow",
        "order": "Order Management Workflow",
        "payment": "Payment Workflow",
        "refund": "Refund Workflow",
        "registration": "Registration Workflow",
        "register": "Registration Workflow",
        "signup": "Registration Workflow",
        "account": "Account Management Workflow",
        "booking": "Booking Workflow",
        "reservation": "Reservation Workflow",
        "approval": "Approval Workflow",
        "subscription": "Subscription Workflow",
        "cart": "Shopping Cart Workflow",
        "invoice": "Invoice Workflow",
        "delivery": "Delivery Workflow",
    }

    STATE_KEYWORDS = {
        "create": "CREATE",
        "register": "REGISTER",
        "submit": "SUBMIT",
        "confirm": "CONFIRM",
        "approve": "APPROVE",
        "complete": "COMPLETE",
        "pay": "PAY",
        "cancel": "CANCEL",
        "refund": "REFUND",
        "delete": "DELETE",
        "update": "UPDATE",
    }

    STATE_TRANSITIONS = {
        "APPROVE",
        "COMPLETE",
        "PAY",
        "REFUND",
        "CANCEL",
        "DELETE",
    }

    VALUE_KEYWORDS = {
        "price",
        "quantity",
        "amount",
        "discount",
        "total",
        "cart",
        "cost",
        "fee",
    }

    OWNERSHIP_KEYWORDS = {
        "user",
        "account",
        "owner",
        "customer",
        "order",
        "booking",
        "reservation",
        "project",
        "resource",
    }

    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        super().__init__(
            agent_name="BusinessLogicAgent",
            llm_provider=llm_provider
        )

    def _normalize_endpoints(
        self,
        context: AgentContext
    ) -> List[Dict[str, Any]]:

        artifacts = context.discovered_artifacts or {}

        endpoints = artifacts.get("endpoints")

        # Check Behavioral Digital Twin
        if not endpoints:
            twin = artifacts.get("behavioral_twin", {})

            if hasattr(twin, "model_dump"):
                twin = twin.model_dump()

            if isinstance(twin, dict):
                endpoints = twin.get("endpoints", [])

        # Fallback to parameters
        if not endpoints:
            endpoints = context.parameters.get("endpoints", [])

        if isinstance(endpoints, dict):
            endpoints = list(endpoints.values())

        normalized = []

        for endpoint in endpoints or []:

            if hasattr(endpoint, "model_dump"):
                endpoint = endpoint.model_dump()

            if isinstance(endpoint, dict):
                normalized.append(endpoint)

        return normalized

    def _identify_workflow(self, path: str) -> Optional[str]:

        path_lower = path.lower()

        for keyword, workflow in self.WORKFLOW_KEYWORDS.items():
            if re.search(rf"(?<![a-z]){re.escape(keyword)}(?![a-z])",
                         path_lower):
                return workflow

        return None

    def _identify_operation(self, path: str, method: str) -> str:

        path_lower = path.lower()

        for keyword, operation in self.STATE_KEYWORDS.items():
            if re.search(rf"(?<![a-z]){re.escape(keyword)}(?![a-z])",
                         path_lower):
                return operation

        method_operations = {
            "POST": "CREATE_OR_SUBMIT",
            "PUT": "UPDATE",
            "PATCH": "UPDATE",
            "DELETE": "DELETE",
            "GET": "READ",
            "HEAD": "READ",
            "OPTIONS": "READ",
        }

        return method_operations.get(method, "UNKNOWN")

    def _safety_classification(
        self,
        method: str
    ) -> SafetyClassification:

        if method in self.MUTATING_METHODS:
            return SafetyClassification.STATE_MODIFYING

        return SafetyClassification.SAFE_READ_ONLY

    async def _run(self, context: AgentContext) -> AgentResult:

        endpoints = self._normalize_endpoints(context)

        workflows: Dict[str, List[Dict[str, Any]]] = {}
        scenarios: List[Dict[str, Any]] = []
        potential_flaws: List[Dict[str, Any]] = []

        scenario_counter = 1

        def add_scenario(
            name: str,
            category: str,
            path: str,
            method: str,
            hypothesis: str,
            safety: SafetyClassification,
            priority: int,
            preconditions: List[str]
        ):

            nonlocal scenario_counter

            scenarios.append({
                "scenario_id": f"BUSINESS-{scenario_counter:03d}",
                "name": name,
                "category": category,
                "target_endpoint": path,
                "method": method,
                "hypothesis": hypothesis,
                "safety_classification": safety.value,
                "priority": priority,
                "preconditions": preconditions,
            })

            scenario_counter += 1

        for endpoint in endpoints:

            path = str(endpoint.get("path", "")).strip()
            method = str(endpoint.get("method", "GET")).upper()

            if not path:
                continue

            # Identify workflow
            workflow = self._identify_workflow(path)

            if not workflow:
                continue

            # Identify operation
            operation = self._identify_operation(path, method)

            workflow_step = {
                "endpoint": path,
                "method": method,
                "operation": operation,
            }

            workflows.setdefault(workflow, []).append(workflow_step)

            endpoint_safety = self._safety_classification(method)

            # Scenario 1: State transition validation
            if operation in self.STATE_TRANSITIONS:

                add_scenario(
                    name=f"{operation} Workflow Validation",
                    category="STATE_TRANSITION",
                    path=path,
                    method=method,
                    hypothesis=(
                        f"The {operation.lower()} operation should only "
                        "be allowed when the resource is in a valid "
                        "preceding state."
                    ),
                    safety=SafetyClassification.STATE_MODIFYING,
                    priority=1,
                    preconditions=[
                        "Use an authorized test environment",
                        "Use synthetic application records",
                        "Require explicit approval before execution",
                        "Verify expected workflow states",
                    ],
                )

                potential_flaws.append({
                    "type": "INVALID_STATE_TRANSITION_REVIEW",
                    "endpoint": path,
                    "description": (
                        f"Review whether {operation.lower()} can be "
                        "performed from an invalid or unexpected state."
                    ),
                    "confirmed": False,
                })

            # Scenario 2: Business value integrity
            path_lower = path.lower()

            if any(
                keyword in path_lower
                for keyword in self.VALUE_KEYWORDS
            ):

                value_safety = (
                    SafetyClassification.STATE_MODIFYING
                    if method in self.MUTATING_METHODS
                    else SafetyClassification.LOW_RISK_PROBE
                )

                add_scenario(
                    name="Business Value Integrity Check",
                    category="VALUE_INTEGRITY",
                    path=path,
                    method=method,
                    hypothesis=(
                        "The application should calculate and validate "
                        "prices, quantities, discounts and totals "
                        "on the server."
                    ),
                    safety=value_safety,
                    priority=2,
                    preconditions=[
                        "Use synthetic products and test prices",
                        "Do not submit real payments",
                        "Use non-destructive test inputs",
                        "Require approval for state-modifying tests",
                    ],
                )

                potential_flaws.append({
                    "type": "VALUE_INTEGRITY_REVIEW",
                    "endpoint": path,
                    "description": (
                        "Review server-side validation of prices, "
                        "quantities, discounts and totals."
                    ),
                    "confirmed": False,
                })

            # Scenario 3: Workflow ownership
            has_identifier = (
                ("{" in path and "}" in path)
                or bool(re.search(r"\bid\b", path_lower))
            )

            has_ownership_keyword = any(
                keyword in path_lower
                for keyword in self.OWNERSHIP_KEYWORDS
            )

            if has_identifier and has_ownership_keyword:

                add_scenario(
                    name="Workflow Ownership Validation",
                    category="OWNERSHIP_VALIDATION",
                    path=path,
                    method=method,
                    hypothesis=(
                        "A user should only perform workflow operations "
                        "on resources they are authorized to control."
                    ),
                    safety=endpoint_safety,
                    priority=1,
                    preconditions=[
                        "Use approved synthetic user accounts",
                        "Use isolated synthetic resources",
                        "Do not access real user records",
                        "Require approval for state-modifying tests",
                    ],
                )

                potential_flaws.append({
                    "type": "WORKFLOW_OWNERSHIP_REVIEW",
                    "endpoint": path,
                    "description": (
                        "Review ownership and authorization checks "
                        "before allowing workflow operations."
                    ),
                    "confirmed": False,
                })

        # Sort workflow steps for consistent output
        for workflow_steps in workflows.values():
            workflow_steps.sort(
                key=lambda step: (
                    step["endpoint"],
                    step["method"]
                )
            )

        return AgentResult(
            agent_name=self.agent_name,
            status=AgentStatus.COMPLETED,
            output_data={
                "endpoints_analyzed": len(endpoints),
                "workflows_discovered": workflows,
                "workflow_count": len(workflows),
                "scenarios_generated": len(scenarios),
                "planned_scenarios": scenarios,
                "potential_flaws": potential_flaws,
                "analysis_type": "STATIC_BUSINESS_LOGIC_ANALYSIS",
                "execution_note": (
                    "Generated scenarios are hypotheses, not confirmed "
                    "business logic vulnerabilities."
                ),
            },
            proposed_actions=[
                {
                    "action": "SUBMIT_BUSINESS_LOGIC_SCENARIOS_FOR_REVIEW",
                    "scenarios_count": len(scenarios),
                }
            ],
            confidence=0.90 if endpoints else 0.20,
        )
