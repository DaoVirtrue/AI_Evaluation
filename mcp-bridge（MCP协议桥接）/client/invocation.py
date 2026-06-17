"""MCP tool invocation (sync/async/streaming)"""
import logging

logger = logging.getLogger("mcp-bridge.invocation")

class ToolInvoker:
    async def invoke(self, connection, tool_name: str, params: dict) -> dict:
        """Invoke a tool synchronously"""
        # JSON-RPC call: {"jsonrpc": "2.0", "method": "tools/call", "params": {...}, "id": 1}
        pass

    async def invoke_stream(self, connection, tool_name: str, params: dict):
        """Invoke a tool with streaming (SSE)"""
        pass
