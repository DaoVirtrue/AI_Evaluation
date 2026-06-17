"""API integration tests for AgentForge"""
import sys, time, requests

BASE = "http://localhost:8001"
PASS = FAIL = 0

def test(name, fn):
    global PASS, FAIL
    try:
        fn()
        print(f"  [PASS] {name}"); PASS += 1
    except Exception as e:
        print(f"  [FAIL] {name}: {e}"); FAIL += 1

def wait(sec=20):
    for _ in range(sec):
        try:
            if requests.get(f"{BASE}/health", timeout=2).status_code == 200: return True
        except: pass
        time.sleep(1)
    return False

def run():
    print("=== AgentForge API Tests ===")
    if not wait(): print("[FAIL] Server not reachable"); sys.exit(1)

    test("health", lambda: requests.get(f"{BASE}/health").json()["status"] == "ok")
    test("run_native", lambda: (
        r := requests.post(f"{BASE}/api/v1/agents/run", json={
            "messages": [{"role": "user", "content": "Hello"}],
            "framework": "native", "model": "claude-sonnet-4-6"
        }), r.status_code == 200 and r.json()["status"] == "success"
    ))
    test("run_langchain", lambda: (
        r := requests.post(f"{BASE}/api/v1/agents/run", json={
            "messages": [{"role": "user", "content": "Test"}],
            "framework": "langchain"
        }), r.status_code == 200
    ))
    test("run_invalid_framework", lambda: (
        r := requests.post(f"{BASE}/api/v1/agents/run", json={
            "messages": [{"role": "user", "content": "x"}], "framework": "invalid"
        }), r.status_code == 400
    ))
    test("run_missing_messages", lambda: (
        r := requests.post(f"{BASE}/api/v1/agents/run", json={}), r.status_code == 422
    ))

    print(f"\n{'='*40}"); print(f"TOTAL: PASS  {PASS}  FAIL  {FAIL}")
    sys.exit(0 if FAIL == 0 else 1)

if __name__ == "__main__": run()
