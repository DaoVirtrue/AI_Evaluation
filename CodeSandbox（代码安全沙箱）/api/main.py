"""
CodeSandbox API — FastAPI application for secure code execution.

Provides HTTP endpoints for executing code in isolated environments
across multiple programming languages.
"""
from __future__ import annotations

import uuid
from typing import Dict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .schemas import (
    ExecutionSpec,
    ExecutionResult,
    ExecutionStatus,
    BatchExecutionRequest,
    BatchExecutionResult,
    RuntimeInfo,
    RuntimesResponse,
    HealthResponse,
    Language,
    TestRunner,
    ResourceUsage,
    TestCaseResult,
)
from ..sandbox.docker_executor import DockerExecutor, LANGUAGE_IMAGE_MAP

# ── Application ────────────────────────────────────────────────────────

app = FastAPI(
    title="CodeSandbox",
    description="多语言代码安全执行沙箱 — Secure Multi-Language Code Execution Sandbox",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Singletons ──────────────────────────────────────────────────────────

executor = DockerExecutor()


# ── Exception Handler ──────────────────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={
            "code": 500,
            "msg": "Internal sandbox error",
            "detail": str(exc) if app.debug else None,
        },
    )


# ── Health ─────────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse)
@app.get("/api/v1/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    docker_ok = await executor.check_docker()
    return HealthResponse(
        status="ok",
        service="code-sandbox",
        available_runtimes=len(LANGUAGE_IMAGE_MAP),
        docker_available=docker_ok,
    )


# ── Execute ────────────────────────────────────────────────────────────

@app.post("/api/v1/execute", response_model=ExecutionResult, status_code=201)
async def execute_code(spec: ExecutionSpec):
    """
    Execute code in a secure sandbox environment.

    Supports 6 programming languages with Docker container isolation.
    Returns unified ExecutionResult regardless of language.
    """
    # Validate language is supported
    if spec.language not in LANGUAGE_IMAGE_MAP:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported language: {spec.language.value}. "
                   f"Supported: {[l.value for l in LANGUAGE_IMAGE_MAP]}",
        )

    result = await executor.execute(spec)
    return result


# ── Batch Execute ──────────────────────────────────────────────────────

@app.post("/api/v1/execute/batch", response_model=BatchExecutionResult, status_code=201)
async def execute_batch(request: BatchExecutionRequest):
    """
    Execute multiple test cases against the same code.

    All test cases share the same code, language, and dependencies.
    Each test case runs independently and results are aggregated.
    """
    spec = request.spec
    spec.test_cases = request.test_cases

    result = await executor.execute(spec)

    passed = sum(1 for r in result.test_results if r.passed)
    failed = len(result.test_results) - passed

    return BatchExecutionResult(
        execution_id=result.execution_id,
        status=result.status,
        passed=passed,
        failed=failed,
        total=len(result.test_results),
        test_results=result.test_results,
        resource_usage=result.resource_usage,
        error_message=result.error_message,
    )


# ── Runtimes ───────────────────────────────────────────────────────────

@app.get("/api/v1/runtimes", response_model=RuntimesResponse)
async def list_runtimes():
    """List available language runtimes and their capabilities."""
    runtime_info = []

    for lang, image in LANGUAGE_IMAGE_MAP.items():
        test_runners = {
            Language.PYTHON: [TestRunner.PYTEST, TestRunner.UNITTEST],
            Language.JAVASCRIPT: [TestRunner.JEST],
            Language.TYPESCRIPT: [TestRunner.JEST],
            Language.GO: [TestRunner.GOTEST],
            Language.JAVA: [TestRunner.JUNIT],
            Language.CPP: [TestRunner.CTEST],
            Language.RUST: [],
        }.get(lang, [])

        versions = {
            Language.PYTHON: ["3.9", "3.10", "3.11", "3.12"],
            Language.JAVASCRIPT: ["18", "20", "22"],
            Language.TYPESCRIPT: ["18", "20", "22"],
            Language.GO: ["1.21", "1.22", "1.23"],
            Language.JAVA: ["17", "21"],
            Language.CPP: ["11", "14", "17", "20"],
            Language.RUST: ["1.75", "1.78"],
        }.get(lang, ["latest"])

        runtime_info.append(RuntimeInfo(
            language=lang,
            versions=versions,
            default_version=versions[-1],
            test_runners=test_runners,
            status="available",
        ))

    return RuntimesResponse(runtimes=runtime_info)


# ── Run module ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8005)
