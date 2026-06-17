"""LangChain adapter for AgentForge"""
from agentforge.agents.base import BaseAgent, Message, ToolDefinition, AgentConfig, AgentResponse, AgentStep, ToolCall
from typing import AsyncIterator
import structlog

logger = structlog.get_logger()

class LangChainAdapter(BaseAgent):
    """Adapter for LangChain / LangGraph agents"""

    @property
    def framework(self) -> str:
        return "langchain"

    async def run(self, messages, tools=None, config=None):
        logger.info("LangChainAdapter.run", framework=self.framework)
        return AgentResponse(
            status="success",
            output=f"[LangChain] Processed {len(messages)} messages",
            steps=[AgentStep(index=0, step_type="llm_call", model=config.model if config else "unknown")],
        )

    async def stream(self, messages, tools=None, config=None) -> AsyncIterator[AgentStep]:
        yield AgentStep(index=0, step_type="llm_call")
