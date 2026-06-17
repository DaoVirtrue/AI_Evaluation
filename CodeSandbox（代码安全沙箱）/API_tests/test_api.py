"""API integration tests for CodeSandbox — requires server running on localhost:8005."""
import sys
import os
import json
import time
from pathlib import Path

import requests

SERVER = "http://localhost:8005"
PASS = 0
FAIL = 0


def check(name: str, condition: bool, detail: str = ""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✓ {name}")
    else:
        FAIL += 1
        print(f"  ✗ {name}  -- {detail}")


def wait_for_server():
    """Wait for server to be reachable."""
    for _ in range(20):
        try:
            r = requests.get(f"{SERVER}/health", timeout=2)
            if r.status_code == 200:
                return True
        except requests.ConnectionError:
            pass
        time.sleep(1)
    return False


def test_health():
    """Test health endpoint."""
    print("\n--- Health ---")
    r = requests.get(f"{SERVER}/health")
    check("Health returns 200", r.status_code == 200)
    data = r.json()
    check("Service is code-sandbox", data.get("service") == "code-sandbox")
    check("Has available_runtimes", "available_runtimes" in data)


def test_list_runtimes():
    """Test runtimes listing."""
    print("\n--- List Runtimes ---")
    r = requests.get(f"{SERVER}/api/v1/runtimes")
    check("Runtimes returns 200", r.status_code == 200)
    data = r.json()
    check("Has runtimes list", "runtimes" in data)
    check("Python in runtimes", any(r["language"] == "python" for r in data["runtimes"]))
    check("JavaScript in runtimes", any(r["language"] == "javascript" for r in data["runtimes"]))


def test_execute_simple():
    """Test simple code execution."""
    print("\n--- Simple Execute ---")
    payload = {
        "language": "python",
        "code": "print('hello')",
        "expected_output": "hello",
        "resources": {
            "timeout_ms": 5000,
            "memory_limit_mb": 256,
            "cpu_limit": 1.0,
            "disk_limit_mb": 512,
            "network_enabled": False,
        },
    }
    r = requests.post(f"{SERVER}/api/v1/execute", json=payload)
    check("Execute returns 201", r.status_code == 201)
    data = r.json()
    check("Has execution_id", "execution_id" in data)
    check("Status is passed", data.get("status") == "passed", f"Got: {data.get('status')}")


def test_execute_with_test_cases():
    """Test batch execution with test cases."""
    print("\n--- Batch Execute ---")
    payload = {
        "spec": {
            "language": "python",
            "code": "def add(a, b): return a + b",
            "resources": {
                "timeout_ms": 5000,
                "memory_limit_mb": 256,
                "cpu_limit": 1.0,
                "disk_limit_mb": 512,
                "network_enabled": False,
            },
        },
        "test_cases": [
            {"name": "test_add", "input": "2 3", "expected": "5"},
            {"name": "test_negative", "input": "-1 1", "expected": "0"},
        ],
    }
    r = requests.post(f"{SERVER}/api/v1/execute/batch", json=payload)
    check("Batch returns 201", r.status_code == 201)
    data = r.json()
    check("Has test_results", "test_results" in data)


def test_execute_security_blocked():
    """Test that dangerous code is blocked."""
    print("\n--- Security Blocking ---")
    payload = {
        "language": "python",
        "code": "import os; os.system('echo hacked')",
        "resources": {
            "timeout_ms": 5000,
            "memory_limit_mb": 256,
            "cpu_limit": 1.0,
            "disk_limit_mb": 512,
            "network_enabled": False,
        },
    }
    r = requests.post(f"{SERVER}/api/v1/execute", json=payload)
    check("Execute returns 201 (security_blocked status)", r.status_code == 201)
    data = r.json()
    check("Status is security_blocked", data.get("status") == "security_blocked",
          f"Got status: {data.get('status')}")


def test_unsupported_language():
    """Test rejection of unsupported languages."""
    print("\n--- Unsupported Language ---")
    payload = {
        "language": "ruby",
        "code": "puts 'hello'",
        "resources": {
            "timeout_ms": 5000,
            "memory_limit_mb": 256,
            "cpu_limit": 1.0,
            "disk_limit_mb": 512,
            "network_enabled": False,
        },
    }
    r = requests.post(f"{SERVER}/api/v1/execute", json=payload)
    check("Ruby is rejected (400)", r.status_code == 400)


def test_validation():
    """Test schema validation."""
    print("\n--- Validation ---")
    # Missing required field 'code'
    payload = {"language": "python"}
    r = requests.post(f"{SERVER}/api/v1/execute", json=payload)
    check("Missing code returns 422", r.status_code == 422)


if __name__ == "__main__":
    print("=" * 60)
    print("CodeSandbox API Integration Tests")
    print("=" * 60)

    if not wait_for_server():
        print("WARNING: Server not reachable — skipping API tests")
        sys.exit(0)

    test_health()
    test_list_runtimes()
    test_execute_simple()
    test_execute_with_test_cases()
    test_execute_security_blocked()
    test_unsupported_language()
    test_validation()

    print(f"\n{'=' * 60}")
    print(f"Results: {PASS} passed, {FAIL} failed")
    print(f"{'=' * 60}")

    sys.exit(FAIL)
