
import logging
from typing import Dict, Any, List

from schemas.agent_io import AgentContext, AgentResult

from agents.discovery_agent.agent import DiscoveryAgent
from agents.planning_agent.agent import PlanningAgent
from agents.verification_agent.agent import VerificationAgent
from agents.reporting_agent.agent import ReportingAgent

from agents.authentication_agent.agent import AuthenticationAgent
from agents.authorization_agent.agent import AuthorizationAgent
from agents.business_logic_agent.agent import BusinessLogicAgent

from intelligence.counterfactual_lab.lab import CounterfactualLab
from intelligence.attack_chain.chain import (
    AttackGraph,
    AttackNode
)
from intelligence.risk_analysis.risk import RiskScoringEngine

from policies.policy_engine import DeterministicPolicyEngine

logger = logging.getLogger("phantom_x.orchestrator")


class AgentOrchestrator:
    """Coordinates the PHANTOM-X security intelligence pipeline."""

    def __init__(
        self,
        policy_engine: DeterministicPolicyEngine = None
    ):
        self.policy_engine = (
            policy_engine or DeterministicPolicyEngine()
        )

        self.discovery_agent = DiscoveryAgent()
        self.planning_agent = PlanningAgent()
        self.verification_agent = VerificationAgent()
        self.reporting_agent = ReportingAgent()

        self.authentication_agent = AuthenticationAgent()
        self.authorization_agent = AuthorizationAgent()
        self.business_logic_agent = BusinessLogicAgent()

        self.counterfactual_lab = CounterfactualLab()

    async def run_discovery_phase(
        self,
        context: AgentContext
    ) -> AgentResult:
        logger.info("Running Discovery Phase")
        return await self.discovery_agent.execute(context)

    async def run_planning_phase(
        self,
        context: AgentContext
    ) -> Dict[str, Any]:

        logger.info("Running Autonomous Planning Phase")

        plan_result = await self.planning_agent.execute(context)

        proposed_scenarios = (
            plan_result.output_data.get("planned_scenarios", [])
        )

        target_host = (
            context.target_url.split("://")[-1].split("/")[0]
            if context.target_url else "localhost"
        )

        policy_eval = self.policy_engine.validate_plan(
            proposed_scenarios,
            target_host
        )

        return {
            "agent_result": plan_result,
            "policy_validation": policy_eval,
            "is_approved_for_execution": policy_eval.is_allowed
        }

    async def run_intelligence_phase(
        self,
        context: AgentContext
    ) -> Dict[str, Any]:

        logger.info("Running Autonomous Attack Intelligence")

        # 1. Generate autonomous security test plan.
        planning = await self.run_planning_phase(context)

        planning_result = planning["agent_result"]

        planned_scenarios = (
            planning_result.output_data.get("planned_scenarios", [])
        )

        planning_summary = {
            "endpoints_analyzed": planning_result.output_data.get(
                "endpoints_analyzed", 0
            ),
            "scenarios_generated": len(planned_scenarios),
            "policy_approved": planning["is_approved_for_execution"],
            "planned_scenarios": planned_scenarios
        }

        # 2. Run authentication, authorization and business logic agents.
        authentication = await self.authentication_agent.execute(
            context
        )

        authorization = await self.authorization_agent.execute(
            context
        )

        business_logic = await self.business_logic_agent.execute(
            context
        )

        # 3. Collect endpoint information.
        artifacts = context.discovered_artifacts or {}
        endpoints = artifacts.get("endpoints", [])

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

        normalized_endpoints = []

        for endpoint in endpoints or []:
            if hasattr(endpoint, "model_dump"):
                endpoint = endpoint.model_dump()

            if isinstance(endpoint, dict):
                normalized_endpoints.append(endpoint)

        # 4. Generate counterfactual hypotheses.
        counterfactual_hypotheses = []

        for endpoint in normalized_endpoints:
            path = endpoint.get("path")

            if not path:
                continue

            hypotheses = self.counterfactual_lab.generate_all_hypotheses(
                endpoint=path
            )

            counterfactual_hypotheses.extend(
                hypothesis.model_dump()
                for hypothesis in hypotheses
            )

        # 5. Build hypothetical attack-chain intelligence.
        attack_graph = AttackGraph(
            chain_title="PHANTOM-X Potential Attack Paths"
        )

        authorization_findings = (
            authorization.output_data.get("findings", [])
        )

        previous_node_id = None

        for index, finding in enumerate(
            authorization_findings,
            start=1
        ):
            node_id = f"AUTHZ-NODE-{index:03d}"

            severity = finding.get("severity", "MEDIUM")

            if severity == "REVIEW":
                severity = "MEDIUM"

            node = AttackNode(
                node_id=node_id,
                phase="AUTHORIZATION_ANALYSIS",
                description=finding.get("description", ""),
                vulnerability_id=finding.get("finding_id", node_id),
                severity=severity
            )

            attack_graph.add_step(
                node,
                incoming_from_id=previous_node_id,
                mechanism=(
                    "Potential relationship between authorization "
                    "review findings; requires verification"
                )
            )

            previous_node_id = node_id

        # 6. Calculate application risk.
        risk_inputs = []
        all_findings = []

        all_findings.extend(
            authentication.output_data.get("flaws_detected", [])
        )

        all_findings.extend(authorization_findings)

        all_findings.extend(
            business_logic.output_data.get("potential_flaws", [])
        )

        for index, finding in enumerate(all_findings, start=1):

            severity = str(
                finding.get("severity", "MEDIUM")
            ).upper()

            if severity not in RiskScoringEngine.SEVERITY_WEIGHTS:
                severity = "MEDIUM"

            risk_inputs.append({
                "id": finding.get(
                    "finding_id",
                    f"INTEL-{index:03d}"
                ),
                "severity": severity,
                "exploitability": "MEDIUM",
                "exposure": "RESTRICTED",
                "business_impact": "MEDIUM",
                "auth_required": True
            })

        risk_analysis = RiskScoringEngine.analyze_application(
            risk_inputs
        )

        # 7. Return complete intelligence results.
        return {
            "planning_analysis": planning_summary,

            "planning_agent_status": planning_result.status,

            "planning_policy_validation": (
                planning["policy_validation"]
            ),

            "authentication_analysis": (
                authentication.output_data
            ),

            "authorization_analysis": (
                authorization.output_data
            ),

            "business_logic_analysis": (
                business_logic.output_data
            ),

            "counterfactual_hypotheses": (
                counterfactual_hypotheses
            ),

            "attack_chain": attack_graph.get_summary(),

            "risk_analysis": risk_analysis,

            "intelligence_summary": {
                "endpoints_analyzed": len(normalized_endpoints),

                "planned_scenarios": len(planned_scenarios),

                "planning_policy_approved": (
                    planning["is_approved_for_execution"]
                ),

                "counterfactual_cases": len(
                    counterfactual_hypotheses
                ),

                "authorization_findings": len(
                    authorization_findings
                ),

                "total_review_findings": len(all_findings),

                "analysis_status": "COMPLETED",

                "verification_required": True
            }
        }

    async def run_verification_phase(
        self,
        context: AgentContext
    ) -> AgentResult:

        logger.info("Running Proof Verification")
        return await self.verification_agent.execute(context)

    async def run_reporting_phase(
        self,
        context: AgentContext
    ) -> AgentResult:

        logger.info("Generating Security Intelligence Report")
        return await self.reporting_agent.execute(context)
