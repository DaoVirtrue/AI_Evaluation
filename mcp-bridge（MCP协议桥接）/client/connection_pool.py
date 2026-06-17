"""MCP Client connection pool"""
import httpx
import asyncio
import logging

logger = logging.getLogger("mcp-bridge.client")

class ConnectionPool:
    def __init__(self, max_idle: int = 10, max_active: int = 50):
        self.max_idle = max_idle
        self.max_active = max_active
        self._clients: dict[str, httpx.AsyncClient] = {}

    async def get_client(self, endpoint: str) -> httpx.AsyncClient:
        """Get or create a client for an endpoint"""
        if endpoint not in self._clients:
            self._clients[endpoint] = httpx.AsyncClient(
                base_url=endpoint,
                timeout=httpx.Timeout(30.0),
                limits=httpx.Limits(max_keepalive_connections=self.max_idle, max_connections=self.max_active),
            )
        return self._clients[endpoint]

    async def close(self):
        for client in self._clients.values():
            await client.aclose()
        self._clients.clear()
