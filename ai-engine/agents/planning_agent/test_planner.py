import pytest
from agents.planning_agent.agent import PlanningAgent
from schemas.agent_io import AgentContext, AgentStatus


@pytest.mark.asyncio
async def test_planner_generates_scenarios():
    agent = PlanningAgent()

    context = AgentContext(
        agent_name="PlanningAgent",
        parameters={
            "endpoints": [
                {
                    "path": "/api/users/{id}",
                    "method": "GET",
                    "required_roles": ["ADMIN", "USER"],
                    "input_schemas": {"id": "integer"}
                },
                {
                    "path": "/api/products",
                    "method": "POST",
                    "required_roles": ["ADMIN"],
                    "input_schemas": {"name": "string"}
                }
            ]
        }
    )

    result = await agent.execute(context)

    assert result.status == AgentStatus.COMPLETED
    assert result.output_data["endpoints_analyzed"] == 2
    assert result.output_data["scenarios_generated"] == 6
    assert len(result.output_data["planned_scenarios"]) == 6


@pytest.mark.asyncio
async def test_planner_recommends_policy_validation():
    agent = PlanningAgent()

    context = AgentContext(
        agent_name="PlanningAgent",
        parameters={"endpoints": []}
    )

    result = await agent.execute(context)

    assert result.status == AgentStatus.COMPLETED
    assert result.proposed_actions[0]["action"] == (
        "SUBMIT_PLAN_FOR_POLICY_VALIDATION"
    )