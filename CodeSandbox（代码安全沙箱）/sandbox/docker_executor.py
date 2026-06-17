"""
Docker Container Executor — the primary sandbox execution backend.

Wraps code execution in isolated Docker containers with:
- Network isolation (--network=none)
- Resource limits (--memory, --cpus)
- Read-only root filesystem (--read-only)
- No privilege escalation (--security-opt=no-new-privileges)
- Automatic container cleanup after execution
- Timeout-based container kill
"""
from __future__ import annotations

import asyncio
import json
import os
import shutil
import tempfile
import time
import uuid
from pathlib import Path
from typing import Dict, Optional, Type

import httpx

from ..api.schemas import (
    ExecutionSpec, ExecutionResult, ExecutionStatus,
    Language, ResourceUsage, TestCaseResult,
)
from ..runtimes.base import BaseRuntime
from ..runtimes.python_runtime import PythonRuntime
from ..security.code_scanner import CodeScanner


# ── Runtime Registry ───────────────────────────────────────────────────

RUNTIME_MAP: Dict[Language, Type[BaseRuntime]] = {
    Language.PYTHON: PythonRuntime,
    # Additional runtimes added as they are implemented:
    # Language.JAVASCRIPT: JavaScriptRuntime,
    # Language.GO: GoRuntime,
    # Language.JAVA: JavaRuntime,
    # Language.CPP: CppRuntime,
    # Language.RUST: RustRuntime,
}

# ── Docker image per language ──────────────────────────────────────────

LANGUAGE_IMAGE_MAP: Dict[Language, str] = {
    Language.PYTHON: "python:3.12-slim",
    Language.JAVASCRIPT: "node:22-slim",
    Language.TYPESCRIPT: "node:22-slim",
    Language.GO: "golang:1.22-alpine",
    Language.JAVA: "openjdk:21-slim",
    Language.CPP: "gcc:13-bookworm",
    Language.RUST: "rust:1.78-slim-bookworm",
}


class DockerExecutor:
    """
    Executes code inside isolated Docker containers.

    Architecture:
        Host API (FastAPI)
            → DockerExecutor.execute(spec)
                → Create temp workspace
                → Write code + files
                → docker run --network=none --read-only --memory=X ...
                → Capture stdout/stderr
                → Parse/score results
                → Destroy container + workspace

    Fallback: If Docker is unavailable, falls back to ProcessExecutor
    for Python (subprocess with resource limits via Python).
    """

    def __init__(self):
        self._docker_available: Optional[bool] = None
        self.scanner = CodeScanner()

    async def check_docker(self) -> bool:
        """Check if Docker is available and accessible."""
        if self._docker_available is not None:
            return self._docker_available

        try:
            proc = await asyncio.create_subprocess_exec(
                "docker", "info",
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await asyncio.wait_for(proc.communicate(), timeout=5.0)
            self._docker_available = proc.returncode == 0
        except Exception:
            self._docker_available = False

        return self._docker_available

    async def execute(self, spec: ExecutionSpec) -> ExecutionResult:
        """Execute code in a Docker container. Falls back to process mode."""
        # Security scan first
        is_safe, reason = self.scanner.scan(spec.code, spec.language)
        if not is_safe:
            return ExecutionResult(
                execution_id=str(uuid.uuid4())[:8],
                status=ExecutionStatus.SECURITY_BLOCKED,
                stderr=f"Code blocked by security scanner: {reason}",
                exit_code=-1,
                resource_usage=ResourceUsage(wall_time_ms=0),
                error_message=reason,
            )

        docker_ok = await self.check_docker()

        if docker_ok:
            return await self._execute_docker(spec)
        else:
            return await self._execute_process(spec)

    async def _execute_docker(self, spec: ExecutionSpec) -> ExecutionResult:
        """Execute code in a Docker container."""
        exec_id = str(uuid.uuid4())[:8]
        workspace = Path(tempfile.mkdtemp(prefix=f"sandbox_{exec_id}_"))
        start_time = time.monotonic()

        try:
            # Write code files
            self._write_workspace(workspace, spec)

            # Prepare test runner script for structured testing
            if spec.test_cases:
                self._write_test_runner(workspace, spec)

            image = LANGUAGE_IMAGE_MAP.get(spec.language, "python:3.12-slim")
            container_name = f"sandbox-{exec_id}"

            # Build docker run command with security hardening
            cmd = [
                "docker", "run",
                "--rm",                              # Auto-remove after execution
                "--name", container_name,
                "--network=none",                     # No network access
                "--read-only",                        # Read-only root filesystem
                f"--memory={spec.resources.memory_limit_mb}m",
                f"--cpus={spec.resources.cpu_limit}",
                "--security-opt=no-new-privileges",   # Prevent privilege escalation
                "--cap-drop=ALL",                     # Drop all capabilities
                "--tmpfs", "/tmp:rw,noexec,nosuid,size=128M",  # Writable /tmp
                "-v", f"{workspace.absolute()}:/code:ro",      # Mount code read-only
                "-w", "/code",
            ]

            # Add environment variables
            for key, value in spec.environment.items():
                cmd.extend(["-e", f"{key}={value}"])

            # Add image
            cmd.append(image)

            # Add execution command
            if spec.test_cases:
                cmd.extend(["python3", "/code/test_runner.py"])
            else:
                cmd.extend(self._get_run_command(spec))

            timeout = spec.resources.timeout_ms / 1000.0 + 5  # +5s for docker overhead

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=timeout,
                )
            except asyncio.TimeoutError:
                # Kill container on timeout
                await self._kill_container(container_name)
                wall_time_ms = int((time.monotonic() - start_time) * 1000)
                return ExecutionResult(
                    execution_id=exec_id,
                    status=ExecutionStatus.TIMEOUT,
                    stderr=f"Container execution timed out after {spec.resources.timeout_ms}ms",
                    exit_code=-1,
                    resource_usage=ResourceUsage(wall_time_ms=wall_time_ms),
                )

            wall_time_ms = int((time.monotonic() - start_time) * 1000)
            stdout = stdout_bytes.decode("utf-8", errors="replace") if stdout_bytes else ""
            stderr = stderr_bytes.decode("utf-8", errors="replace") if stderr_bytes else ""

            # Parse structured test results if available
            if spec.test_cases:
                return self._parse_test_results(exec_id, stdout, stderr, proc.returncode or 0, wall_time_ms)

            # Simple execution — check output
            status = ExecutionStatus.PASSED
            if spec.expected_output is not None:
                if stdout.strip() != spec.expected_output.strip():
                    status = ExecutionStatus.FAILED
            if proc.returncode != 0:
                status = ExecutionStatus.ERROR

            return ExecutionResult(
                execution_id=exec_id,
                status=status,
                stdout=stdout,
                stderr=stderr,
                exit_code=proc.returncode or 0,
                resource_usage=ResourceUsage(wall_time_ms=wall_time_ms),
            )

        except Exception as e:
            wall_time_ms = int((time.monotonic() - start_time) * 1000)
            return ExecutionResult(
                execution_id=exec_id,
                status=ExecutionStatus.ERROR,
                stderr=str(e),
                exit_code=-1,
                resource_usage=ResourceUsage(wall_time_ms=wall_time_ms),
                error_message=str(e),
            )
        finally:
            # Clean up workspace
            try:
                shutil.rmtree(workspace, ignore_errors=True)
            except Exception:
                pass

    async def _execute_process(self, spec: ExecutionSpec) -> ExecutionResult:
        """Fallback: execute code via local subprocess (no Docker isolation)."""
        exec_id = str(uuid.uuid4())[:8]
        workspace = Path(tempfile.mkdtemp(prefix=f"sandbox_{exec_id}_"))

        try:
            runtime_cls = RUNTIME_MAP.get(spec.language, PythonRuntime)
            runtime = runtime_cls(spec, workspace)

            compiled = await runtime.compile()
            if not compiled:
                return runtime._make_result(
                    status=ExecutionStatus.ERROR,
                    stderr="Compilation failed",
                    exit_code=1,
                    wall_time_ms=0,
                )

            if spec.test_cases:
                result = await runtime.run_tests()
            else:
                result = await runtime.run()

            result.execution_id = exec_id
            return result

        except Exception as e:
            return ExecutionResult(
                execution_id=exec_id,
                status=ExecutionStatus.ERROR,
                stderr=str(e),
                exit_code=-1,
                resource_usage=ResourceUsage(wall_time_ms=0),
                error_message=str(e),
            )
        finally:
            try:
                shutil.rmtree(workspace, ignore_errors=True)
            except Exception:
                pass

    def _write_workspace(self, workspace: Path, spec: ExecutionSpec) -> None:
        """Write code and additional files to workspace."""
        ext_map = {
            Language.PYTHON: ".py",
            Language.JAVASCRIPT: ".js",
            Language.TYPESCRIPT: ".ts",
            Language.GO: ".go",
            Language.JAVA: ".java",
            Language.CPP: ".cpp",
            Language.RUST: ".rs",
        }
        ext = ext_map.get(spec.language, ".txt")
        main_file = workspace / f"solution{ext}"
        main_file.write_text(spec.code, encoding="utf-8")

        for filename, content in spec.files.items():
            file_path = workspace / filename
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")

    def _write_test_runner(self, workspace: Path, spec: ExecutionSpec) -> None:
        """Write a test runner script for structured test execution."""
        ext_map = {
            Language.PYTHON: ".py",
            Language.JAVASCRIPT: ".js",
        }
        ext = ext_map.get(spec.language, ".py")
        main_file = f"solution{ext}"

        # Generate a Python test runner that imports solution and runs test cases
        runner = f'''"""Auto-generated test runner for code sandbox."""
import sys
import json
import importlib.util

# Load the solution module
spec_mod = importlib.util.spec_from_file_location("solution", "{main_file}")
solution = importlib.util.module_from_spec(spec_mod)
spec_mod.loader.exec_module(solution)

test_cases = {json.dumps([{
    "name": tc.name,
    "input": tc.input,
    "expected": tc.expected,
} for tc in spec.test_cases])}

results = []
for tc in test_cases:
    try:
        # Try to call the first function in the module
        func_name = [n for n in dir(solution) if not n.startswith("_") and callable(getattr(solution, n))][0]
        func = getattr(solution, func_name)
        if tc["input"]:
            actual = str(func(tc["input"]))
        else:
            actual = str(func())
        passed = actual.strip() == tc["expected"].strip()
        results.append({{
            "name": tc["name"],
            "passed": passed,
            "expected": tc["expected"],
            "actual": actual,
        }})
    except Exception as e:
        results.append({{
            "name": tc["name"],
            "passed": False,
            "expected": tc["expected"],
            "actual": "",
            "error": str(e),
        }})

print(json.dumps(results))
'''
        runner_file = workspace / "test_runner.py"
        runner_file.write_text(runner, encoding="utf-8")

    def _parse_test_results(
        self, exec_id: str, stdout: str, stderr: str,
        exit_code: int, wall_time_ms: int,
    ) -> ExecutionResult:
        """Parse JSON test results from the test runner output."""
        try:
            test_data = json.loads(stdout)
            results = [
                TestCaseResult(
                    name=t["name"],
                    passed=t["passed"],
                    expected=t.get("expected", ""),
                    actual=t.get("actual", ""),
                    error=t.get("error"),
                )
                for t in test_data
            ]
            passed = sum(1 for r in results if r.passed)
            failed = len(results) - passed
            status = ExecutionStatus.PASSED if failed == 0 else ExecutionStatus.FAILED

            return ExecutionResult(
                execution_id=exec_id,
                status=status,
                stdout=stdout,
                stderr=stderr,
                exit_code=exit_code,
                test_results=results,
                resource_usage=ResourceUsage(wall_time_ms=wall_time_ms),
            )
        except json.JSONDecodeError:
            return ExecutionResult(
                execution_id=exec_id,
                status=ExecutionStatus.ERROR,
                stdout=stdout,
                stderr=stderr,
                exit_code=exit_code,
                resource_usage=ResourceUsage(wall_time_ms=wall_time_ms),
                error_message="Failed to parse test runner output",
            )

    def _get_run_command(self, spec: ExecutionSpec) -> list:
        """Get the docker run command for a given language."""
        ext_map = {
            Language.PYTHON: ["python3", "solution.py"],
            Language.JAVASCRIPT: ["node", "solution.js"],
            Language.TYPESCRIPT: ["npx", "ts-node", "solution.ts"],
            Language.GO: ["sh", "-c", "go run solution.go"],
            Language.JAVA: ["sh", "-c", "javac solution.java && java Solution"],
            Language.CPP: ["sh", "-c", "g++ -O2 solution.cpp -o solution && ./solution"],
            Language.RUST: ["sh", "-c", "rustc solution.rs -o solution && ./solution"],
        }
        return ext_map.get(spec.language, ["python3", "solution.py"])

    async def _kill_container(self, container_name: str) -> None:
        """Force-kill a Docker container."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "docker", "kill", container_name,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await asyncio.wait_for(proc.communicate(), timeout=5.0)
        except Exception:
            pass
