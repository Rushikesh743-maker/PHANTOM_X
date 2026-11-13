
from typing import Optional, Any, Dict, List

from agents.base import BaseAgent
from schemas.agent_io import AgentContext, AgentResult, AgentStatus
from llm.providers.base import LLMProvider
from agents.planning_agent.planner import AutonomousTestPlanner


class PlanningAgent(BaseAgent):
    """Autonomous agent generating security test plans."""

    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        super().__init__(
            agent_name="PlanningAgent",
            llm_provider=llm_provider
        )
        self.planner = AutonomousTestPlanner()

    async def _run(self, context: AgentContext) -> AgentResult:

        artifacts = context.discovered_artifacts or {}

        # Obtain Behavioral Digital Twin data
        twin = artifacts.get("behavioral_twin", {})

        if hasattr(twin, "model_dump"):
            twin = twin.model_dump()

        # Obtain endpoint information
        endpoints = artifacts.get("endpoints")

        if not endpoints and isinstance(twin, dict):
            endpoints = twin.get("endpoints", [])

        if not endpoints:
            endpoints = context.parameters.get("endpoints", [])

        if isinstance(endpoints, dict):
            endpoints = list(endpoints.values())

        # Normalize endpoint objects
        normalized_endpoints = []

        for endpoint in endpoints or []:
            if hasattr(endpoint, "model_dump"):
                endpoint = endpoint.model_dump()

            if isinstance(endpoint, dict):
                normalized_endpoints.append(endpoint)

        # Extract additional Behavioral Digital Twin intelligence
        workflow_sequences = []
        role_hierarchy = {}

        if isinstance(twin, dict):
            workflow_sequences = twin.get("workflow_sequences", [])
            role_hierarchy = twin.get("role_hierarchy", {})

        # Generate scenarios using endpoint and workflow intelligence
        scenarios = self.planner.generate_plan(
            normalized_endpoints,
            workflow_sequences=workflow_sequences,
            role_hierarchy=role_hierarchy
        )

        planned_scenarios = [
            scenario.model_dump()
            for scenario in scenarios
        ]

        return AgentResult(
            agent_name=self.agent_name,
            status=AgentStatus.COMPLETED,
            output_data={
                "planned_scenarios": planned_scenarios,
                "endpoints_analyzed": len(normalized_endpoints),
                "scenarios_generated": len(planned_scenarios),
                "workflows_analyzed": len(workflow_sequences),
                "role_hierarchy_available": bool(role_hierarchy)
            },
            proposed_actions=[
                {
                    "action": "SUBMIT_PLAN_FOR_POLICY_VALIDATION",
                    "scenarios_count": len(planned_scenarios)
                }
            ],
            confidence=0.90 if normalized_endpoints else 0.30
        )
