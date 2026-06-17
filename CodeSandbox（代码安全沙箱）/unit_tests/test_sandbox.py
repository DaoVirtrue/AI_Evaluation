"""Unit tests for CodeSandbox — security, executor, and runtime modules."""
import sys
import os
import json
import tempfile
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Test counter
PASS = 0
FAIL = 0


def check(name: str, condition: bool, detail: str = ""):
    """Simple test assertion."""
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✓ {name}")
    else:
        FAIL += 1
        print(f"  ✗ {name}  -- {detail}")


# ── Test: Security Scanner ─────────────────────────────────────────────

def test_code_scanner():
    """Test the security code scanner."""
    print("\n--- Code Scanner Tests ---")

    from security.code_scanner import CodeScanner
    from api.schemas import Language

    scanner = CodeScanner()

    # Safe code
    safe, reason = scanner.scan("def add(a, b): return a + b", Language.PYTHON)
    check("Safe Python code passes", safe, reason)

    safe, reason = scanner.scan("print(sum([1, 2, 3]))", Language.PYTHON)
    check("Simple print passes", safe, reason)

    # Unsafe code
    safe, reason = scanner.scan("import os; os.system('rm -rf /')", Language.PYTHON)
    check("os.system() blocked", not safe, reason)

    safe, reason = scanner.scan("eval('print(1)')", Language.PYTHON)
    check("eval() blocked", not safe, reason)

    safe, reason = scanner.scan("import subprocess; subprocess.run(['ls'])", Language.PYTHON)
    check("subprocess blocked", not safe, reason)

    safe, reason = scanner.scan("import requests; requests.get('http://evil.com')", Language.PYTHON)
    check("HTTP request blocked", not safe, reason)

    safe, reason = scanner.scan("__import__('os').system('ls')", Language.PYTHON)
    check("__import__() blocked", not safe, reason)

    # Null byte check
    safe, reason = scanner.scan("hello\x00world", Language.PYTHON)
    check("Null bytes blocked", not safe, reason)

    # Size check
    huge_code = "x" * 600_000
    safe, reason = scanner.scan(huge_code, Language.PYTHON)
    check("Oversized code blocked", not safe, reason)

    # JS patterns
    safe, reason = scanner.scan("const { exec } = require('child_process')", Language.JAVASCRIPT)
    check("Node.js child_process blocked", not safe, reason)

    safe, reason = scanner.scan("eval('1+1')", Language.JAVASCRIPT)
    check("JS eval() blocked", not safe, reason)


# ── Test: Schemas ──────────────────────────────────────────────────────

def test_schemas():
    """Test Pydantic schema validation."""
    print("\n--- Schema Tests ---")

    from api.schemas import ExecutionSpec, ResourceSpec, Language, ExecutionStatus

    # Valid spec
    spec = ExecutionSpec(
        language=Language.PYTHON,
        code="print('hello')",
        resources=ResourceSpec(timeout_ms=1000, memory_limit_mb=128),
    )
    check("Valid ExecutionSpec created", spec.language == Language.PYTHON)
    check("Default version is 'latest'", spec.version == "latest")
    check("Default network_enabled is False", not spec.resources.network_enabled)

    # Validation: code too short
    try:
        ExecutionSpec(language=Language.PYTHON, code="")
        check("Empty code rejected", False, "Should have raised validation error")
    except Exception:
        check("Empty code rejected", True)

    # Validation: timeout bounds
    try:
        ResourceSpec(timeout_ms=10)  # Below minimum of 100
        check("Timeout < 100ms rejected", False, "Should have raised validation error")
    except Exception:
        check("Timeout < 100ms rejected", True)

    try:
        ResourceSpec(timeout_ms=120000)  # Above maximum of 60000
        check("Timeout > 60s rejected", False, "Should have raised validation error")
    except Exception:
        check("Timeout > 60s rejected", True)

    # Status enum
    check("ExecutionStatus.PASSED exists", ExecutionStatus.PASSED.value == "passed")
    check("ExecutionStatus.SECURITY_BLOCKED exists", ExecutionStatus.SECURITY_BLOCKED.value == "security_blocked")


# ── Test: Network Policy ───────────────────────────────────────────────

def test_network_policy():
    """Test network policy module."""
    print("\n--- Network Policy Tests ---")

    from sandbox.network_policy import (
        NetworkPolicy, get_docker_network_args, is_domain_allowed
    )

    args = get_docker_network_args(NetworkPolicy.NONE)
    check("NONE policy gives --network=none", "--network=none" in args)

    args = get_docker_network_args(NetworkPolicy.FULL)
    check("FULL policy gives empty args", args == [])

    check("pypi.org is allowed", is_domain_allowed("pypi.org"))
    check("random-site.com is NOT allowed", not is_domain_allowed("random-site.com"))
    check("evil.com is NOT allowed", not is_domain_allowed("evil.com"))


# ── Test: Resource Limiter ─────────────────────────────────────────────

def test_resource_limiter():
    """Test resource limiter module."""
    print("\n--- Resource Limiter Tests ---")

    from sandbox.resource_limiter import get_docker_resource_args, get_ulimit_args
    from api.schemas import ResourceSpec

    spec = ResourceSpec(memory_limit_mb=256, cpu_limit=1.0, disk_limit_mb=512)
    args = get_docker_resource_args(spec)

    check("Memory limit in args", "--memory=256m" in args)
    check("CPU limit in args", "--cpus=1.0" in args)
    check("Disk limit in args", "--storage-opt=size=512M" in args)

    ulimits = get_ulimit_args()
    check("nproc limit present", any("nproc=64" in u for u in ulimits))
    check("nofile limit present", any("nofile=256" in u for u in ulimits))


# ── Run All Tests ──────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("CodeSandbox Unit Tests")
    print("=" * 60)

    test_code_scanner()
    test_schemas()
    test_network_policy()
    test_resource_limiter()

    print(f"\n{'=' * 60}")
    print(f"Results: {PASS} passed, {FAIL} failed")
    print(f"{'=' * 60}")

    sys.exit(FAIL)
