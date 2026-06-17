"""Sliding window rate limiter for MCP tools"""
import time
import logging
from collections import defaultdict

logger = logging.getLogger("mcp-bridge.rate-limiter")

class RateLimiter:
    def __init__(self, default_max: int = 30, window_seconds: int = 60):
        self.default_max = default_max
        self.window = window_seconds
        self._windows: dict[str, list[float]] = defaultdict(list)
        self._per_tool_limits: dict[str, int] = {}

    def set_limit(self, tool: str, max_per_minute: int):
        self._per_tool_limits[tool] = max_per_minute

    def check(self, user: str, tool: str) -> bool:
        """Check if request is within rate limit. Returns True if allowed."""
        key = f"{user}:{tool}"
        now = time.time()

        # Clean expired entries
        self._windows[key] = [t for t in self._windows[key] if now - t < self.window]

        max_allowed = self._per_tool_limits.get(tool, self.default_max)
        if len(self._windows[key]) >= max_allowed:
            logger.warning(f"Rate limit exceeded: {key}")
            return False

        self._windows[key].append(now)
        return True
