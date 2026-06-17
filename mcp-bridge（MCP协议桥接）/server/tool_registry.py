"""Tool Registry - register, discover, invoke tools"""
import logging
from typing import Optional

logger = logging.getLogger("mcp-bridge.registry")

class ToolDefinition:
    def __init__(self, name: str, description: str, input_schema: dict, handler_ref: str | None = None):
        self.name = name
        self.description = description
        self.inputSchema = input_schema
        self.handler_ref = handler_ref

    def to_dict(self):
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.inputSchema,
        }


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, ToolDefinition] = {}
        self._handlers: dict[str, callable] = {}
        self._register_defaults()

    def _register_defaults(self):
        """Register some default tools for demonstration"""
        self.register(
            "echo", "Echo back the input message",
            {"type": "object", "properties": {"message": {"type": "string"}}, "required": ["message"]},
            "_echo_handler"
        )
        self._handlers["_echo_handler"] = lambda params: {"echo": params.get("message", "")}

        self.register(
            "web_search", "Search the web for information",
            {"type": "object", "properties": {"query": {"type": "string", "description": "Search query"}}, "required": ["query"]},
            "_search_handler"
        )
        self._handlers["_search_handler"] = lambda params: {"results": [f"Mock result for: {params.get('query', '')}"]}

        self.register(
            "calculator", "Perform basic arithmetic",
            {"type": "object", "properties": {"expression": {"type": "string", "description": "Math expression"}}, "required": ["expression"]},
            "_calc_handler"
        )
        self._handlers["_calc_handler"] = lambda params: {"result": str(eval(params.get("expression", "0")))}

    def register(self, name: str, description: str, input_schema: dict, handler_ref: str | None = None):
        self._tools[name] = ToolDefinition(name, description, input_schema, handler_ref)
        logger.info(f"Tool registered: {name}")

    def get(self, name: str) -> Optional[ToolDefinition]:
        return self._tools.get(name)

    def list_tools(self, user: str | None = None) -> list[dict]:
        return [t.to_dict() for t in self._tools.values()]

    def count(self) -> int:
        return len(self._tools)

    async def invoke(self, name: str, params: dict) -> dict:
        tool = self._tools.get(name)
        if not tool:
            raise ValueError(f"Tool not found: {name}")

        handler = self._handlers.get(tool.handler_ref) if tool.handler_ref else None
        if handler:
            return handler(params)
        raise ValueError(f"No handler for tool: {name}")
