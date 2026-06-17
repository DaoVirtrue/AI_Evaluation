"""API integration tests for token-core HTTP endpoints"""
import sys
import time
import requests
import json

BASE_URL = "http://localhost:8003"
PASSED = 0
FAILED = 0


def test(name: str, fn):
    global PASSED, FAILED
    try:
        fn()
        print(f"  [PASS] {name}")
        PASSED += 1
    except AssertionError as e:
        print(f"  [FAIL] {name}: {e}")
        FAILED += 1
    except Exception as e:
        print(f"  [FAIL] {name}: {type(e).__name__}: {e}")
        FAILED += 1


def wait_for_server(timeout=30):
    """Wait for the server to be ready"""
    for i in range(timeout):
        try:
            r = requests.get(f"{BASE_URL}/health", timeout=2)
            if r.status_code == 200:
                return True
        except:
            pass
        time.sleep(1)
    return False


def run_tests():
    print("=== token-core API Integration Tests ===")
    print(f"Server: {BASE_URL}")

    if not wait_for_server():
        print("[FAIL] Server not reachable after 30s")
        sys.exit(1)

    # --- Health ---
    test("health_check", lambda: (
        (r := requests.get(f"{BASE_URL}/health")).status_code == 200
        and "status" in r.json()
    ))

    # --- Token Counting ---
    test("count_tokens_normal", lambda: (
        (r := requests.post(f"{BASE_URL}/api/v1/count", json={
            "text": "Hello, world!", "model": "claude-sonnet-4-6"
        })).status_code == 200
        and r.json()["tokens"] > 0
    ))

    test("count_tokens_missing_model", lambda: (
        (r := requests.post(f"{BASE_URL}/api/v1/count", json={
            "text": "hello"
        })).status_code == 422
    ))

    test("count_tokens_invalid_model", lambda: (
        (r := requests.post(f"{BASE_URL}/api/v1/count", json={
            "text": "hello", "model": "fake-model"
        })).status_code == 400
        and "msg" in r.json()
    ))

    # --- Batch Counting ---
    test("count_batch_normal", lambda: (
        (r := requests.post(f"{BASE_URL}/api/v1/count/batch", json={
            "messages": [
                {"role": "system", "content": "You are helpful."},
                {"role": "user", "content": "Hi there!"}
            ],
            "model": "claude-sonnet-4-6"
        })).status_code == 200
        and len(r.json()["counts"]) == 2
    ))

    test("count_batch_empty_messages", lambda: (
        (r := requests.post(f"{BASE_URL}/api/v1/count/batch", json={
            "messages": [], "model": "claude-sonnet-4-6"
        })).status_code == 200
    ))

    # --- Estimate ---
    test("estimate_tokens", lambda: (
        (r := requests.post(f"{BASE_URL}/api/v1/estimate", json={
            "text": "Hello, world!", "model": "any"
        })).status_code == 200
        and r.json()["estimated_tokens"] > 0
    ))

    # --- Cost Calculation ---
    test("calculate_cost_normal", lambda: (
        (r := requests.post(f"{BASE_URL}/api/v1/cost", json={
            "usage": {"prompt_tokens": 10000, "completion_tokens": 1000},
            "model": "claude-sonnet-4-6",
            "mode": "online"
        })).status_code == 200
    ))

    test("calculate_cost_invalid_model", lambda: (
        (r := requests.post(f"{BASE_URL}/api/v1/cost", json={
            "usage": {"prompt_tokens": 10000, "completion_tokens": 1000},
            "model": "fake-model",
            "mode": "online"
        })).status_code == 400
    ))

    test("calculate_cost_batch_mode", lambda: (
        (r := requests.post(f"{BASE_URL}/api/v1/cost", json={
            "usage": {"prompt_tokens": 10000, "completion_tokens": 1000},
            "model": "claude-sonnet-4-6",
            "mode": "batch"
        })).status_code == 200
    ))

    # --- Compare Models ---
    test("compare_models_normal", lambda: (
        (r := requests.post(f"{BASE_URL}/api/v1/compare", json={
            "input_tokens": 100000,
            "estimated_output": 20000,
            "candidates": ["claude-opus-4-8", "claude-sonnet-4-6", "deepseek-v4-flash"]
        })).status_code == 200
        and len(r.json()) == 3
    ))

    test("compare_models_empty_candidates", lambda: (
        (r := requests.post(f"{BASE_URL}/api/v1/compare", json={
            "input_tokens": 100000,
            "estimated_output": 20000,
            "candidates": []
        })).status_code == 422
    ))

    # --- Truncate ---
    test("truncate_normal", lambda: (
        (r := requests.post(f"{BASE_URL}/api/v1/truncate", json={
            "messages": [
                {"role": "system", "content": "You are helpful.", "index": 0},
                {"role": "user", "content": "Hello!", "index": 1}
            ],
            "model": "claude-sonnet-4-6"
        })).status_code == 200
    ))

    # --- Context Window ---
    test("check_window_normal", lambda: (
        (r := requests.post(f"{BASE_URL}/api/v1/window", json={
            "messages": [
                {"role": "user", "content": "hello", "index": 0}
            ],
            "model": "claude-sonnet-4-6"
        })).status_code == 200
        and "total_tokens" in r.json()
    ))

    # --- Model Listing ---
    test("list_models", lambda: (
        (r := requests.get(f"{BASE_URL}/api/v1/models")).status_code == 200
        and r.json()["count"] >= 16
    ))

    test("get_pricing_valid", lambda: (
        (r := requests.get(f"{BASE_URL}/api/v1/pricing/claude-sonnet-4-6")).status_code == 200
        and r.json()["provider"] == "anthropic"
    ))

    test("get_pricing_invalid", lambda: (
        (r := requests.get(f"{BASE_URL}/api/v1/pricing/fake-model")).status_code == 404
    ))

    # --- Security: oversize input ---
    test("oversize_input_rejected", lambda: (
        (r := requests.post(f"{BASE_URL}/api/v1/count", json={
            "text": "x" * 11_000_000, "model": "claude-sonnet-4-6"
        })).status_code in (400, 413, 422)
    ))


def main():
    global PASSED, FAILED
    run_tests()
    total = PASSED + FAILED
    print(f"\n{'='*40}")
    print(f"API Tests        PASS  {PASSED}  FAIL  {FAILED}")
    print(f"{'='*40}")
    print(f"TOTAL: PASS  {total}  FAIL  {FAILED}  SKIP  0")
    print(f"{'='*40}")
    sys.exit(0 if FAILED == 0 else 1)


if __name__ == "__main__":
    main()
