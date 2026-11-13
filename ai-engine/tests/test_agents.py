
import pytest
import uuid

from schemas.agent_io import AgentContext, AgentStatus
from agents.discovery_agent.agent import DiscoveryAgent
from agents.planning_agent.agent import PlanningAgent
from agents.verification_agent.agent import VerificationAgent
from policies.policy_engine import DeterministicPolicyEngine


@pytest.mark.asyncio
async def test_discovery_agent_execution():
    agent = DiscoveryAgent()

    context = AgentContext(
        agent_name="DiscoveryAgent",
        target_url="http://localhost:3000",
        scan_id=uuid.uuid4(),
    )

    result = await agent.execute(context)

    assert result.status == AgentStatus.COMPLETED
    assert result.agent_name == "DiscoveryAgent"
    assert "discovered_endpoints" in result.output_data


@pytest.mark.asyncio
async def test_planning_agent_and_policy_engine_validation():
    planning_agent = PlanningAgent()

    context = AgentContext(
        agent_name="PlanningAgent",
        target_url="http://localhost:3000",
        scan_id=uuid.uuid4(),
        discovered_artifacts={
            "endpoints": [
                {
                    "path": "/api/users/{id}",
                    "method": "GET",
                    "auth_required": True,
                    "required_roles": ["USER"],
                    "input_schemas": {
                        "id": {
                            "type": "integer",
                            "required": True
                        }
                    }
                },
                {
                    "path": "/api/products",
                    "method": "GET",
                    "auth_required": False,
                    "required_roles": [],
                    "input_schemas": {}
                }
            ]
        }
    )

    result = await planning_agent.execute(context)

    assert result.status == AgentStatus.COMPLETED
    assert result.agent_name == "PlanningAgent"

    scenarios = result.output_data.get("planned_scenarios", [])

    assert len(scenarios) > 0
    assert result.output_data["endpoints_analyzed"] == 2
    assert result.output_data["scenarios_generated"] == len(scenarios)

    policy = DeterministicPolicyEngine(
        allowed_hosts=["localhost"]
    )

    eval_res = policy.validate_plan(
        scenarios,
        "localhost"
    )

    assert eval_res.is_allowed is True
    assert len(eval_res.approved_actions) == len(scenarios)


def test_deterministic_policy_blocks_unauthorized_scope():
    policy = DeterministicPolicyEngine(
        allowed_hosts=["localhost"]
    )

    malicious_scenario = [
        {
            "scenario_id": "malicious-01",
            "parameters": "DROP TABLE users;",
            "safety_classification": "SAFE_READ_ONLY"
        }
    ]

    # Test 1: Unauthorized target must be blocked
    res_scope = policy.validate_plan(
        malicious_scenario,
        "unauthorized-external-site.com"
    )

    assert res_scope.is_allowed is False
    assert len(res_scope.violations) > 0

    # Test 2: Destructive SQL must be blocked
    res_destruct = policy.validate_plan(
        malicious_scenario,
        "localhost"
    )

    assert res_destruct.is_allowed is False

    assert any(
        "destructive" in violation.lower()
        for violation in res_destruct.violations
    )
