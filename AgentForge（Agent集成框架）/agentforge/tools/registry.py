"""Tool registry for AgentForge"""
from agentforge.agents.base import ToolDefinition
import structlog

logger = structlog.get_logger()

class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, ToolDefinition] = {}
        self._register_defaults()

    def _register_defaults(self):
        self.register(ToolDefinition("echo", "Echo input", {"type": "object", "properties": {"message": {"type": "string"}}}))
        self.register(ToolDefinition("calculator", "Math calculation", {"type": "object", "properties": {"expression": {"type": "string"}}}))

    def register(self, tool: ToolDefinition):
        self._tools[tool.name] = tool

    def list(self) -> list[ToolDefinition]:
        return list(self._tools.values())

    def get(self, name: str) -> ToolDefinition | None:
        return self._tools.get(name)
