import asyncio

from agents.planning_agent.agent import PlanningAgent
from schemas.agent_io import AgentContext


async def main():
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

    print("\nSTATUS:", result.status)
    print("\nOUTPUT:", result.output_data)
    print("\nPROPOSED ACTIONS:", result.proposed_actions)


asyncio.run(main())