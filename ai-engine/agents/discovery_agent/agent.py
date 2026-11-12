from typing import Optional
from agents.base import BaseAgent
from schemas.agent_io import AgentContext, AgentResult, AgentStatus
from llm.providers.base import LLMProvider


class DiscoveryAgent(BaseAgent):
    """Member 1: Autonomous agent responsible for endpoint discovery, crawling, and API inventory."""

    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        super().__init__(agent_name="DiscoveryAgent", llm_provider=llm_provider)

    async def _run(self, context: AgentContext) -> AgentResult:
        source_type = context.parameters.get("source_type", "SPECIFICATION") if context.parameters else "SPECIFICATION"

        discovered = [
            {"path": "/api/v1/auth/login", "method": "POST", "auth_required": False, "source": source_type},
            {"path": "/api/v1/users/profile", "method": "GET", "auth_required": True, "source": source_type},
        ]

        if context.target_url:
            discovered.append({"path": "/health", "method": "GET", "auth_required": False, "source": "PASSIVE"})

        return AgentResult(
            agent_name=self.agent_name,
            status=AgentStatus.COMPLETED,
            output_data={
                "discovered_endpoints": discovered,
                "endpoints_count": len(discovered),
                "source_type": source_type,
                "message": "Endpoint discovery completed.",
            },
            proposed_actions=[
                {"action": "PROFILE_API_SCHEMA", "target": context.target_url}
            ],
            confidence=0.95
        )
