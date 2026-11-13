
import asyncio

from agents.authorization_agent.agent import AuthorizationAgent
from schemas.agent_io import AgentContext


async def main():

    agent = AuthorizationAgent()

    context = AgentContext(
        agent_name="AuthorizationAgent",
        parameters={
            "endpoints": [
                {
                    "path": "/api/users/{id}",
                    "method": "GET",
                    "auth_required": True,
                    "authentication": {
                        "auth_type": "BEARER",
                        "roles_permitted": ["ADMIN", "USER"]
                    }
                },
                {
                    "path": "/api/tenants/{tenant_id}/projects",
                    "method": "GET",
                    "auth_required": True,
                    "required_roles": ["ADMIN"]
                },
                {
                    "path": "/api/public",
                    "method": "GET",
                    "auth_required": False
                }
            ]
        }
    )

    result = await agent.execute(context)

    print("\nSTATUS:", result.status)
    print("\nOUTPUT:", result.output_data)
    print("\nPROPOSED ACTIONS:", result.proposed_actions)


if __name__ == "__main__":
    asyncio.run(main())
