
import asyncio
from uuid import uuid4
from pprint import pprint

from orchestration.orchestrator import AgentOrchestrator
from schemas.agent_io import AgentContext


async def main():

    orchestrator = AgentOrchestrator()

    context = AgentContext(
        agent_name="PHANTOM-X",
        target_application_id=uuid4(),
        target_url="http://localhost:8000",
        scan_id=uuid4(),
        discovered_artifacts={
            "endpoints": [
                {
                    "path": "/api/users/{id}",
                    "method": "GET",
                    "auth_required": True,
                    "required_roles": ["USER"],
                    "authentication": {
                        "auth_type": "BEARER",
                        "roles_permitted": ["USER"]
                    },
                    "parameters": {
                        "id": "string"
                    }
                },
                {
                    "path": "/api/payments/{id}/refund",
                    "method": "POST",
                    "auth_required": True,
                    "required_roles": ["ADMIN"],
                    "authentication": {
                        "auth_type": "BEARER",
                        "roles_permitted": ["ADMIN"]
                    }
                }
            ]
        }
    )

    # PHASE 1: Autonomous planning and policy validation
    planning_result = await orchestrator.run_planning_phase(context)

    # PHASE 2: Autonomous attack intelligence
    intelligence_result = await orchestrator.run_intelligence_phase(context)

    print("\nPHANTOM-X INTELLIGENCE INTEGRATION")
    print("=" * 50)

    print("\n1. PLANNING ANALYSIS")
    print("-" * 50)

    plan_agent = planning_result["agent_result"]

    print("Status:", plan_agent.status)
    print("Planned Scenarios:")
    pprint(plan_agent.output_data.get("planned_scenarios", []))

    print("\n2. POLICY VALIDATION")
    print("-" * 50)

    policy = planning_result["policy_validation"]

    if hasattr(policy, "model_dump"):
        policy = policy.model_dump()

    pprint(policy)

    print(
        "\nApproved for execution:",
        planning_result["is_approved_for_execution"]
    )

    print("\n3. INTELLIGENCE SUMMARY")
    print("-" * 50)
    pprint(intelligence_result["intelligence_summary"])

    print("\n4. AUTHENTICATION ANALYSIS")
    pprint(intelligence_result["authentication_analysis"])

    print("\n5. AUTHORIZATION ANALYSIS")
    pprint(intelligence_result["authorization_analysis"])

    print("\n6. BUSINESS LOGIC ANALYSIS")
    pprint(intelligence_result["business_logic_analysis"])

    print("\n7. COUNTERFACTUAL CASES")
    print("Total:", len(intelligence_result["counterfactual_hypotheses"]))
    pprint(intelligence_result["counterfactual_hypotheses"])

    print("\n8. ATTACK CHAIN")
    pprint(intelligence_result["attack_chain"])

    print("\n9. RISK ANALYSIS")
    pprint(intelligence_result["risk_analysis"])


if __name__ == "__main__":
    asyncio.run(main())
