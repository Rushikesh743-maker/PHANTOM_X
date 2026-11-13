
import asyncio

from agents.authentication_agent.agent import AuthenticationAgent
from schemas.agent_io import AgentContext


async def main():

    agent = AuthenticationAgent()

    context = AgentContext(
        agent_name="AuthenticationAgent",
        parameters={
            "endpoints": [
                {
                    "path": "/api/users",
                    "method": "GET",
                    "auth_required": True,
                    "authentication": {
                        "auth_type": "BEARER",
                        "roles_permitted": ["ADMIN", "USER"]
                    }
                },
                {
                    "path": "/api/admin",
                    "method": "POST",
                    "auth_required": True,
                    "authentication": {
                        "auth_type": "NONE"
                    }
                },
                {
                    "path": "/api/public",
                    "method": "GET",
                    "auth_required": False,
                    "authentication": {
                        "auth_type": "NONE"
                    }
                }
            ]
        }
    )

    result = await agent.execute(context)

    print("STATUS:", result.status)
    print("OUTPUT:", result.output_data)
    print("PROPOSED ACTIONS:", result.proposed_actions)


if __name__ == "__main__":
    asyncio.run(main())
