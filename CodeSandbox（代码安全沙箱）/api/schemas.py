"""
CodeSandbox API Schemas — Pydantic models for request/response validation.

Defines the unified ExecutionSpec and ExecutionResult types that enable
"移花接木" — transparent cross-language, cross-environment code execution.
"""
from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


# ── Language & Status Enums ────────────────────────────────────────────

class Language(str, Enum):
    """Supported programming languages."""
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    GO = "go"
    JAVA = "java"
    CPP = "cpp"
    RUST = "rust"


class ExecutionStatus(str, Enum):
    """Unified execution result status across all languages."""
    PASSED = "passed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    ERROR = "error"
    SECURITY_BLOCKED = "security_blocked"


class TestRunner(str, Enum):
    """Supported test frameworks per language."""
    PYTEST = "pytest"
    UNITTEST = "unittest"
    JEST = "jest"
    GOTEST = "gotest"
    JUNIT = "junit"
    CTEST = "ctest"


# ── Resource Specification ─────────────────────────────────────────────

class ResourceSpec(BaseModel):
    """Resource limits for code execution."""
    timeout_ms: int = Field(default=5000, ge=100, le=60000, description="Execution timeout in milliseconds")
    memory_limit_mb: int = Field(default=256, ge=16, le=4096, description="Memory limit in MB")
    cpu_limit: float = Field(default=1.0, ge=0.1, le=4.0, description="CPU core limit")
    disk_limit_mb: int = Field(default=512, ge=64, le=4096, description="Disk space limit in MB")
    network_enabled: bool = Field(default=False, description="Whether network access is allowed")


# ── Core Execution Spec ────────────────────────────────────────────────

class ExecutionSpec(BaseModel):
    """
    Cross-language, cross-environment unified execution specification.

    This is the "移花接木" abstraction — one interface for all languages.
    New languages only need to implement BaseRuntime's 4 methods.
    """
    language: Language = Field(..., description="Target programming language")
    version: str = Field(default="latest", description="Language version e.g. 3.12, 22, 1.22")
    code: str = Field(..., min_length=1, max_length=500000, description="Source code to execute")
    files: Dict[str, str] = Field(
        default_factory=dict,
        description="Additional files for multi-file projects {filename: content}"
    )
    entrypoint: Optional[str] = Field(default=None, description="Entry file/function for multi-file projects")
    test_input: Optional[str] = Field(default=None, description="Stdin input for the program")
    expected_output: Optional[str] = Field(default=None, description="Expected stdout output for simple matching")
    dependencies: List[str] = Field(
        default_factory=list,
        description="Package dependencies e.g. ['numpy==1.24.0', 'fastapi>=0.115']"
    )
    environment: Dict[str, str] = Field(
        default_factory=dict,
        description="Environment variables to inject"
    )
    resources: ResourceSpec = Field(default_factory=ResourceSpec, description="Resource limits")
    test_runner: Optional[TestRunner] = Field(default=None, description="Test framework for structured testing")
    test_cases: List["TestCaseSpec"] = Field(
        default_factory=list,
        description="Structured test cases with inputs and expected outputs"
    )
    pre_install: List[str] = Field(
        default_factory=list,
        description="Pre-install commands e.g. ['apt-get install -y libxml2']"
    )


class TestCaseSpec(BaseModel):
    """A single test case definition."""
    name: str = Field(..., description="Test case name/identifier")
    input: Optional[str] = Field(default=None, description="Test input (stdin or function arguments)")
    expected: str = Field(..., description="Expected output")
    timeout_ms: Optional[int] = Field(default=None, description="Per-test timeout override")


class TestCaseResult(BaseModel):
    """Result of a single test case execution."""
    name: str
    passed: bool
    input: Optional[str] = None
    expected: str
    actual: str
    error: Optional[str] = None
    duration_ms: Optional[int] = None


class ResourceUsage(BaseModel):
    """Measured resource consumption."""
    wall_time_ms: int
    cpu_time_ms: Optional[int] = None
    memory_used_kb: Optional[int] = None


# ── Core Execution Result ──────────────────────────────────────────────

class ExecutionResult(BaseModel):
    """
    Cross-language, cross-environment unified execution result.

    Returned identically regardless of language or runtime used.
    """
    execution_id: str = Field(..., description="Unique execution identifier (UUID)")
    status: ExecutionStatus = Field(..., description="Overall execution status")
    stdout: str = Field(default="", description="Standard output")
    stderr: str = Field(default="", description="Standard error")
    exit_code: int = Field(default=-1, description="Process exit code")
    test_results: List[TestCaseResult] = Field(
        default_factory=list,
        description="Individual test case results"
    )
    resource_usage: ResourceUsage = Field(
        default_factory=lambda: ResourceUsage(wall_time_ms=0),
        description="Measured resource consumption"
    )
    error_message: Optional[str] = Field(default=None, description="Error details if status is error/security_blocked")


# ── Batch Execution ────────────────────────────────────────────────────

class BatchExecutionRequest(BaseModel):
    """Batch execution of multiple test cases against the same code."""
    spec: ExecutionSpec = Field(..., description="Base execution spec (code, language, deps, etc.)")
    test_cases: List[TestCaseSpec] = Field(..., min_length=1, max_length=1000, description="Test cases to run")


class BatchExecutionResult(BaseModel):
    """Aggregate result for batch execution."""
    execution_id: str
    status: ExecutionStatus
    passed: int = 0
    failed: int = 0
    total: int = 0
    test_results: List[TestCaseResult] = Field(default_factory=list)
    resource_usage: ResourceUsage = Field(default_factory=lambda: ResourceUsage(wall_time_ms=0))
    error_message: Optional[str] = None


# ── Runtime Info ───────────────────────────────────────────────────────

class RuntimeInfo(BaseModel):
    """Information about an available language runtime."""
    language: Language
    versions: List[str]
    default_version: str
    test_runners: List[TestRunner]
    status: str = "available"  # available | offline | error


class RuntimesResponse(BaseModel):
    """Response for listing available runtimes."""
    runtimes: List[RuntimeInfo]


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = "ok"
    service: str = "code-sandbox"
    available_runtimes: int
    docker_available: bool
    warm_pool_size: int = 0


# ── Forward reference resolution ───────────────────────────────────────
ExecutionSpec.model_rebuild()
