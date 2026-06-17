"""
Timeout Guard — ensures code execution does not exceed time limits.

Uses asyncio.wait_for with SIGKILL fallback for subprocess trees.
"""
from __future__ import annotations

import asyncio
import os
import signal
from typing import Optional


class TimeoutGuard:
    """
    Guards code execution against timeout.

    Two-stage approach:
        1. Soft timeout: asyncio.wait_for(timeout)
        2. Hard timeout: docker kill / SIGKILL if still alive
    """

    def __init__(self, timeout_ms: int):
        self.timeout_ms = timeout_ms
        self._timer: Optional[asyncio.Task] = None

    @property
    def timeout_seconds(self) -> float:
        return self.timeout_ms / 1000.0

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._timer:
            self._timer.cancel()

    async def run_with_timeout(self, coro):
        """
        Run a coroutine with timeout.
        Raises asyncio.TimeoutError if the coroutine does not complete in time.
        """
        return await asyncio.wait_for(coro, timeout=self.timeout_seconds)


def kill_process_tree(pid: int) -> None:
    """
    Kill a process and all its children.
    Linux/Mac: uses SIGKILL with process group.
    Windows: uses taskkill /T /F.
    """
    try:
        if os.name == "nt":
            # Windows
            import subprocess
            subprocess.run(
                ["taskkill", "/T", "/F", "/PID", str(pid)],
                capture_output=True,
                timeout=5,
            )
        else:
            # Unix
            os.killpg(os.getpgid(pid), signal.SIGKILL)
    except (ProcessLookupError, OSError):
        pass  # Process already dead
