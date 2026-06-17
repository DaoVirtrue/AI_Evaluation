"""API integration tests for mcp-bridge"""
import sys
import time
import requests

BASE = "http://localhost:8004"
PASS = 0
FAIL = 0

def test(name, fn):
    global PASS, FAIL
    try:
        fn()
        print(f"  [PASS] {name}")
        PASS += 1
    except Exception as e:
        print(f"  [FAIL] {name}: {e}")
        FAIL += 1

def wait(sec=20):
    for _ in range(sec):
        try:
            if requests.get(f"{BASE}/health", timeout=2).status_code == 200:
                return True
        except: pass
        time.sleep(1)
    return False

def run():
    print("=== mcp-bridge API Tests ===")
    if not wait():
        print("[FAIL] Server not reachable"); sys.exit(1)

    test("health", lambda: requests.get(f"{BASE}/health").json()["status"] == "ok")

    # tools/list
    test("tools_list", lambda: (
        r := requests.post(f"{BASE}/mcp", json={"jsonrpc": "2.0", "method": "tools/list", "id": 1}),
        len(r.json().get("result", {}).get("tools", [])) > 0
    ))

    # tools/call normal
    test("tools_call_echo", lambda: (
        r := requests.post(f"{BASE}/mcp", json={"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "echo", "arguments": {"message": "hello"}}, "id": 2}),
        "echo" in str(r.json())
    ))

    # tools/call missing name
    test("tools_call_missing_name", lambda: (
        r := requests.post(f"{BASE}/mcp", json={"jsonrpc": "2.0", "method": "tools/call", "params": {}, "id": 3}),
        "error" in r.json()
    ))

    # initialize
    test("initialize", lambda: (
        r := requests.post(f"{BASE}/mcp", json={"jsonrpc": "2.0", "method": "initialize", "id": 4}),
        r.json()["result"]["protocolVersion"] == "2024-11-05"
    ))

    # method not found
    test("method_not_found", lambda: (
        r := requests.post(f"{BASE}/mcp", json={"jsonrpc": "2.0", "method": "nonexistent", "id": 5}),
        r.json()["error"]["code"] == -32601
    ))

    # REST invoke tool
    test("rest_invoke", lambda: (
        r := requests.post(f"{BASE}/api/v1/tools/invoke", json={"tool": "echo", "params": {"message": "test"}}),
        r.status_code == 200 and "result" in r.json()
    ))

    # REST discover tools
    test("rest_discover", lambda: requests.get(f"{BASE}/api/v1/tools/discover").status_code == 200)

    # audit logs
    test("audit_logs", lambda: requests.get(f"{BASE}/api/v1/audit/logs").status_code == 200)

    # protocol conversion (via bridge functions, tested in unit_tests)
    from bridge.mcp_to_openai import mcp_to_openai_function
    result = mcp_to_openai_function({"name": "test", "description": "desc", "inputSchema": {"type": "object"}})
    assert result["type"] == "function"
    assert result["function"]["name"] == "test"
    print("  [PASS] mcp_to_openai_function")

    global PASS; PASS += 1

    print(f"\n{'='*40}")
    print(f"TOTAL: PASS  {PASS}  FAIL  {FAIL}  SKIP  0")
    sys.exit(0 if FAIL == 0 else 1)

if __name__ == "__main__":
    run()
