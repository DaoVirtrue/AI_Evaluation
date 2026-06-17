"""Adapter registry - map framework names to adapter classes"""
from agentforge.agents.langchain_adapter import LangChainAdapter
from agentforge.agents.openai_agents_adapter import OpenAIAgentsAdapter
from agentforge.agents.native_adapter import NativeAdapter

ADAPTERS = {
    "langchain": LangChainAdapter,
    "openai_agents": OpenAIAgentsAdapter,
    "native": NativeAdapter,
}

def get_adapter(framework: str):
    cls = ADAPTERS.get(framework)
    if not cls:
        raise ValueError(f"Unknown framework: {framework}. Available: {list(ADAPTERS.keys())}")
    return cls()
