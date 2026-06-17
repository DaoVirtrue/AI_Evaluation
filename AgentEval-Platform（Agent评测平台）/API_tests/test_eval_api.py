"""API tests for AgentEval Platform"""
import sys, time, requests

BASE = "http://localhost:8000"
P = F = 0

def test(n, fn):
    global P, F
    try: fn(); print(f"  [PASS] {n}"); P += 1
    except Exception as e: print(f"  [FAIL] {n}: {e}"); F += 1

def wait():
    for _ in range(20):
        try:
            if requests.get(f"{BASE}/health", timeout=2).status_code == 200: return True
        except: pass
        time.sleep(1)
    return False

def run():
    print("=== AgentEval API Tests ===")
    if not wait(): print("[FAIL] Server not reachable"); sys.exit(1)

    test("health", lambda: requests.get(f"{BASE}/health").json()["status"] == "ok")

    # Create evaluation
    test("create_eval", lambda: (
        r := requests.post(f"{BASE}/api/v1/evaluations", json={"name": "Test Eval", "agent_config": {"model": "claude-sonnet-4-6"}, "max_cases": 5}),
        r.status_code == 201 and "id" in r.json()
    ))
    eval_id = requests.post(f"{BASE}/api/v1/evaluations", json={"name": "T2", "max_cases": 2}).json()["id"]

    test("get_eval", lambda: requests.get(f"{BASE}/api/v1/evaluations/{eval_id}").status_code == 200)
    test("get_status", lambda: requests.get(f"{BASE}/api/v1/evaluations/{eval_id}/status").status_code == 200)
    test("list_evals", lambda: requests.get(f"{BASE}/api/v1/evaluations").json()["total"] > 0)
    test("cancel_eval", lambda: requests.delete(f"{BASE}/api/v1/evaluations/{eval_id}").status_code == 200)

    # Missing params
    test("missing_name_422", lambda: requests.post(f"{BASE}/api/v1/evaluations", json={}).status_code == 422)
    # Not found
    test("not_found_404", lambda: requests.get(f"{BASE}/api/v1/evaluations/nonexistent").status_code == 404)

    print(f"\n{'='*40}"); print(f"TOTAL: PASS  {P}  FAIL  {F}")
    sys.exit(0 if F == 0 else 1)

if __name__ == "__main__": run()
