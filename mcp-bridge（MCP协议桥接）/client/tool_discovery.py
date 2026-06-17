"""MCP Tool discovery with caching"""
import time
import logging

logger = logging.getLogger("mcp-bridge.discovery")

class ToolDiscovery:
    def __init__(self, ttl: int = 300):
        self.ttl = ttl
        self._cache: dict[str, tuple[list[dict], float]] = {}

    async def discover(self, connection, source: str) -> list[dict]:
        """Discover tools from an MCP source with caching"""
        now = time.time()
        if source in self._cache:
            tools, cached_at = self._cache[source]
            if now - cached_at < self.ttl:
                return tools

        # In production: send tools/list JSON-RPC to the MCP server
        tools = []  # placeholder
        self._cache[source] = (tools, now)
        return tools

    def invalidate(self, source: str):
        self._cache.pop(source, None)
