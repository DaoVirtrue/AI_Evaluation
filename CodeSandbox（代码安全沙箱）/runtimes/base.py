"""
Base Runtime — abstract interface for all language runtimes.

The "移花接木" pattern:
    Every language runtime implements exactly these 4 methods.
    The sandbox orchestrator never knows which language it's running.
    Add a new language → implement these 4 methods → it just works.
"""
from __future__ import annotations

import abc
import tempfile
from pathlib import Path
from typing import Dict, List, Optional

from ..api.schemas import ExecutionSpec, ExecutionResult, ExecutionStatus, ResourceUsage


class BaseRuntime(abc.ABC):
    """
    Abstract base class for all language runtimes.

    Subclasses implement:
        compile()     — compile/build the code (no-op for interpreted languages)
        run()         — execute the code and capture output
        run_tests()   — run structured test cases against the code
        cleanup()     — clean up build artifacts

    The sandbox layer handles:
        - Docker container lifecycle
        - Resource limits (CPU, memory, disk)
        - Network isolation
        - Timeout enforcement
        - Dependency installation
        - Environment variables
    """

    def __init__(self, spec: ExecutionSpec, work_dir: Path):
        self.spec = spec
        self.work_dir = work_dir
        self._compiled = False

    @property
    @abc.abstractmethod
    def language(self) -> str:
        """Return the language identifier (e.g., 'python', 'go')."""

    @property
    @abc.abstractmethod
    def default_version(self) -> str:
        """Return the default language version."""

    @property
    @abc.abstractmethod
    def source_extension(self) -> str:
        """Return the source file extension (e.g., '.py', '.js')."""

    @abc.abstractmethod
    async def compile(self) -> bool:
        """
        Compile/build the source code.
        Returns True on success, False on compilation failure.
        For interpreted languages, this is a no-op (always returns True).
        """

    @abc.abstractmethod
    async def run(self) -> ExecutionResult:
        """
        Execute the code and return the result.
        Captures stdout, stderr, exit code, and timing.
        """

    @abc.abstractmethod
    async def run_tests(self) -> ExecutionResult:
        """
        Execute structured test cases against the code.
        Each test case runs independently and results are aggregated.
        """

    @abc.abstractmethod
    async def cleanup(self) -> None:
        """Clean up build artifacts and temporary files."""

    def _write_code_file(self) -> Path:
        """Write the source code to a file in the work directory."""
        ext = self.source_extension
        file_path = self.work_dir / f"solution{ext}"
        file_path.write_text(self.spec.code, encoding="utf-8")
        return file_path

    def _write_additional_files(self) -> Dict[str, Path]:
        """Write additional files for multi-file projects."""
        paths: Dict[str, Path] = {}
        for filename, content in self.spec.files.items():
            file_path = self.work_dir / filename
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")
            paths[filename] = file_path
        return paths

    def _make_result(
        self,
        status: ExecutionStatus,
        stdout: str = "",
        stderr: str = "",
        exit_code: int = -1,
        wall_time_ms: int = 0,
        cpu_time_ms: Optional[int] = None,
        memory_kb: Optional[int] = None,
        error_message: Optional[str] = None,
    ) -> ExecutionResult:
        """Factory method to create a standardized ExecutionResult."""
        import uuid
        return ExecutionResult(
            execution_id=str(uuid.uuid4())[:8],
            status=status,
            stdout=stdout,
            stderr=stderr,
            exit_code=exit_code,
            resource_usage=ResourceUsage(
                wall_time_ms=wall_time_ms,
                cpu_time_ms=cpu_time_ms,
                memory_used_kb=memory_kb,
            ),
            error_message=error_message,
        )
