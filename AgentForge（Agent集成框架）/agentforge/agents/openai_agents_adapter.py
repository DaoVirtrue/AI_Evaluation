"""OpenAI Agents SDK adapter for AgentForge"""
from agentforge.agents.base import BaseAgent, Message, ToolDefinition, AgentConfig, AgentResponse, AgentStep
from typing import AsyncIterator
import structlog

logger = structlog.get_logger()

class OpenAIAgentsAdapter(BaseAgent):
    @property
    def framework(self) -> str:
        return "openai_agents"

    async def run(self, messages, tools=None, config=None):
        logger.info("OpenAIAgentsAdapter.run", framework=self.framework)
        return AgentResponse(
            status="success",
            output=f"[OpenAI Agents] Processed {len(messages)} messages",
            steps=[AgentStep(index=0, step_type="llm_call", model=config.model if config else "gpt-5.5")],
        )

    async def stream(self, messages, tools=None, config=None) -> AsyncIterator[AgentStep]:
        yield AgentStep(index=0, step_type="llm_call")
