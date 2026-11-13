
import asyncio

from agents.business_logic_agent.agent import BusinessLogicAgent
from schemas.agent_io import AgentContext


async def main():

    agent = BusinessLogicAgent()

    context = AgentContext(
        agent_name="BusinessLogicAgent",
        parameters={
            "endpoints": [
                {
                    "path": "/api/orders/{id}/checkout",
                    "method": "POST"
                },
                {
                    "path": "/api/payments/{id}/refund",
                    "method": "POST"
                },
                {
                    "path": "/api/cart/price",
                    "method": "GET"
                },
                {
                    "path": "/api/bookings/{id}/cancel",
                    "method": "POST"
                },
                {
                    "path": "/api/users/{id}/account",
                    "method": "GET"
                }
            ]
        }
    )

    result = await agent.execute(context)

    print("\nSTATUS:", result.status)
    print("\nWORKFLOWS:", result.output_data["workflows_discovered"])
    print("\nSCENARIOS:", result.output_data["planned_scenarios"])
    print("\nPOTENTIAL FLAWS:", result.output_data["potential_flaws"])


if __name__ == "__main__":
    asyncio.run(main())
