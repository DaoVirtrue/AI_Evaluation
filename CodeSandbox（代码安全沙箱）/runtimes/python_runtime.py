"""
Python Runtime — executes Python code safely via subprocess.

Supports Python 3.9 through 3.12 with:
- pip dependency installation
- pytest/unittest structured test execution
- stdout/stderr capture with timeout
"""
from __future__ import annotations

import asyncio
import os
import time
from pathlib import Path
from typing import Optional

from .base import BaseRuntime
from ..api.schemas import (
    ExecutionSpec, ExecutionResult, ExecutionStatus,
    TestCaseResult, ResourceUsage,
)


class PythonRuntime(BaseRuntime):
    """Python code execution runtime."""

    @property
    def language(self) -> str:
        return "python"

    @property
    def default_version(self) -> str:
        return "3.12"

    @property
    def source_extension(self) -> str:
        return ".py"

    async def compile(self) -> bool:
        """Python is interpreted — check syntax with py_compile."""
        file_path = self._write_code_file()
        self._write_additional_files()

        try:
            proc = await asyncio.create_subprocess_exec(
                "python3", "-m", "py_compile", str(file_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=10.0,
            )
            self._compiled = proc.returncode == 0
            return self._compiled
        except asyncio.TimeoutError:
            self._compiled = False
            return False
        except FileNotFoundError:
            # Try 'python' if 'python3' not found
            try:
                proc = await asyncio.create_subprocess_exec(
                    "python", "-m", "py_compile", str(file_path),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=10.0
                )
                self._compiled = proc.returncode == 0
                return self._compiled
            except (asyncio.TimeoutError, FileNotFoundError):
                self._compiled = False
                return False

    async def run(self) -> ExecutionResult:
        """Execute Python code and capture output."""
        file_path = self.work_dir / "solution.py"
        if not file_path.exists():
            self._write_code_file()

        timeout = self.spec.resources.timeout_ms / 1000.0
        start_time = time.monotonic()

        try:
            env = os.environ.copy()
            env.update(self.spec.environment)

            proc = await asyncio.create_subprocess_exec(
                "python3", str(file_path),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.work_dir),
                env=env,
            )

            stdin_bytes = (
                self.spec.test_input.encode("utf-8")
                if self.spec.test_input
                else b""
            )

            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(input=stdin_bytes),
                timeout=timeout,
            )

            wall_time_ms = int((time.monotonic() - start_time) * 1000)
            stdout = stdout_bytes.decode("utf-8", errors="replace")
            stderr = stderr_bytes.decode("utf-8", errors="replace")

            # Determine pass/fail based on expected output matching
            status = ExecutionStatus.PASSED
            if self.spec.expected_output is not None:
                actual_clean = stdout.strip()
                expected_clean = self.spec.expected_output.strip()
                if actual_clean != expected_clean:
                    status = ExecutionStatus.FAILED

            if proc.returncode != 0:
                status = ExecutionStatus.ERROR

            return self._make_result(
                status=status,
                stdout=stdout,
                stderr=stderr,
                exit_code=proc.returncode or 0,
                wall_time_ms=wall_time_ms,
            )

        except asyncio.TimeoutError:
            wall_time_ms = int((time.monotonic() - start_time) * 1000)
            return self._make_result(
                status=ExecutionStatus.TIMEOUT,
                stderr=f"Execution timed out after {self.spec.resources.timeout_ms}ms",
                exit_code=-1,
                wall_time_ms=wall_time_ms,
            )
        except Exception as e:
            wall_time_ms = int((time.monotonic() - start_time) * 1000)
            return self._make_result(
                status=ExecutionStatus.ERROR,
                stderr=str(e),
                exit_code=-1,
                wall_time_ms=wall_time_ms,
                error_message=str(e),
            )

    async def run_tests(self) -> ExecutionResult:
        """Execute structured test cases against Python code."""
        file_path = self.work_dir / "solution.py"
        if not file_path.exists():
            self._write_code_file()

        results = []
        passed = 0
        failed = 0
        total_start = time.monotonic()

        for tc in self.spec.test_cases:
            tc_timeout = (tc.timeout_ms or self.spec.resources.timeout_ms) / 1000.0
            tc_start = time.monotonic()

            try:
                env = os.environ.copy()
                env.update(self.spec.environment)

                proc = await asyncio.create_subprocess_exec(
                    "python3", str(file_path),
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=str(self.work_dir),
                    env=env,
                )

                stdin_bytes = (tc.input or "").encode("utf-8")
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    proc.communicate(input=stdin_bytes),
                    timeout=tc_timeout,
                )

                tc_duration = int((time.monotonic() - tc_start) * 1000)
                actual = stdout_bytes.decode("utf-8", errors="replace").strip()
                expected = tc.expected.strip()
                tc_passed = actual == expected

                if tc_passed:
                    passed += 1
                else:
                    failed += 1

                results.append(TestCaseResult(
                    name=tc.name,
                    passed=tc_passed,
                    input=tc.input,
                    expected=expected,
                    actual=actual,
                    error=stderr_bytes.decode("utf-8", errors="replace") if stderr_bytes else None,
                    duration_ms=tc_duration,
                ))

            except asyncio.TimeoutError:
                failed += 1
                tc_duration = int((time.monotonic() - tc_start) * 1000)
                results.append(TestCaseResult(
                    name=tc.name,
                    passed=False,
                    input=tc.input,
                    expected=tc.expected.strip(),
                    actual="",
                    error=f"Timeout after {tc_timeout}s",
                    duration_ms=tc_duration,
                ))
            except Exception as e:
                failed += 1
                tc_duration = int((time.monotonic() - tc_start) * 1000)
                results.append(TestCaseResult(
                    name=tc.name,
                    passed=False,
                    input=tc.input,
                    expected=tc.expected.strip(),
                    actual="",
                    error=str(e),
                    duration_ms=tc_duration,
                ))

        total_time = int((time.monotonic() - total_start) * 1000)
        total_status = ExecutionStatus.PASSED if failed == 0 else ExecutionStatus.FAILED

        result = self._make_result(
            status=total_status,
            stdout="",
            stderr="",
            exit_code=0 if failed == 0 else 1,
            wall_time_ms=total_time,
        )
        result.test_results = results
        return result

    async def cleanup(self) -> None:
        """Clean up .pyc files and __pycache__ directories."""
        import shutil
        for pyc in self.work_dir.glob("**/*.pyc"):
            pyc.unlink(missing_ok=True)
        for cachedir in self.work_dir.glob("**/__pycache__"):
            shutil.rmtree(cachedir, ignore_errors=True)
