"""Base Agent abstract class - all framework adapters implement this"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import AsyncIterator, Optional
import time
import uuid
import structlog

logger = structlog.get_logger()

@dataclass
class Message:
    role: str  # system | user | assistant | tool
    content: str
    index: int = 0

@dataclass
class ToolDefinition:
    name: str
    description: str
    input_schema: dict

@dataclass
class AgentConfig:
    model: str = "claude-sonnet-4-6"
    max_tokens: int = 64_000
    temperature: float = 0.7
    tools: list[ToolDefinition] = field(default_factory=list)
    system_prompt: str = ""
    middleware_config: dict = field(default_factory=dict)
    routing_strategy: str = "cost_optimal"  # cost_optimal | latency_optimal | capability_optimal
    max_cost_per_call: float = 1.0
    max_latency_ms: int = 30_000

@dataclass
class ToolCall:
    name: str
    params: dict
    result: Optional[dict] = None
    error: Optional[str] = None

@dataclass
class AgentStep:
    index: int
    step_type: str  # llm_call | tool_call | thinking | output | error
    model: Optional[str] = None
    input: Optional[str] = None
    output: Optional[str] = None
    tool_name: Optional[str] = None
    tool_input: Optional[dict] = None
    tool_output: Optional[dict] = None
    tool_error: Optional[str] = None
    token_usage: Optional[dict] = None
    latency_ms: Optional[int] = None
    timestamp: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))

@dataclass
class AgentResponse:
    session_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    status: str = "success"  # success | error | timeout
    output: str = ""
    steps: list[AgentStep] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    total_tokens: int = 0
    total_cost: float = 0.0
    total_latency_ms: int = 0
    error_message: Optional[str] = None

class BaseAgent(ABC):
    """All framework adapters must implement this interface"""

    @abstractmethod
    async def run(
        self, messages: list[Message], tools: list[ToolDefinition] | None = None, config: AgentConfig | None = None
    ) -> AgentResponse:
        ...

    @abstractmethod
    async def stream(
        self, messages: list[Message], tools: list[ToolDefinition] | None = None, config: AgentConfig | None = None
    ) -> AsyncIterator[AgentStep]:
        ...

    @property
    @abstractmethod
    def framework(self) -> str:
        ...
