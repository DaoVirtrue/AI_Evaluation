"""MCP tool call result cache"""
import time
import logging
logger = logging.getLogger("mcp-bridge.cache")

class ToolCache:
    def __init__(self, ttl: int = 60):
        self.ttl = ttl
        self._cache: dict[str, tuple[dict, float]] = {}

    def get(self, key: str) -> dict | None:
        entry = self._cache.get(key)
        if entry and time.time() - entry[1] < self.ttl:
            return entry[0]
        return None

    def set(self, key: str, result: dict):
        self._cache[key] = (result, time.time())

    def invalidate(self, key: str):
        self._cache.pop(key, None)
