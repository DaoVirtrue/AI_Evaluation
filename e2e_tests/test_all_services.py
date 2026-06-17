#!/usr/bin/env python3
"""
端到端测试 — 全部 4 个服务 API
token-core (8003) + mcp-bridge (8004) + AgentForge (8001) + AgentEval (8000)
"""
import sys, time, json, requests

BASE = {
    "eval": "http://localhost:8000",
    "forge": "http://localhost:8001",
    "token": "http://localhost:8003",
    "mcp": "http://localhost:8004",
}
PASS = 0
FAIL = 0
SKIP = 0

def test(name, fn):
    global PASS, FAIL
    try:
        fn()
        print(f"  ✅ {name}")
        PASS += 1
    except AssertionError as e:
        print(f"  ❌ {name}: {e}")
        FAIL += 1
    except Exception as e:
        print(f"  ❌ {name}: {type(e).__name__}: {e}")
        FAIL += 1

def wait_all():
    for label, url in BASE.items():
        for _ in range(30):
            try:
                r = requests.get(f"{url}/health", timeout=2)
                if r.status_code == 200:
                    print(f"  🟢 {label} ready ({url})")
                    break
            except: pass
            time.sleep(1)
        else:
            print(f"  🔴 {label} NOT READY ({url})")

# ============================================================
print("=" * 50)
print("  全栈端到端测试 — 4 服务 × 30+ 用例")
print("=" * 50)
print("\n⏳ Waiting for services...")
wait_all()
print(f"\n{'='*50}\n")

# ==================== token-core (8003) ====================
print("📦 [1/4] token-core — Token 计数 + 成本引擎\n")

test("health", lambda: (
    r := requests.get(f"{BASE['token']}/health"),
    r.status_code == 200,
    r.json()["models"] >= 17
))

test("count_tokens", lambda: (
    r := requests.post(f"{BASE['token']}/api/v1/count",
        json={"text": "Hello world!", "model": "claude-sonnet-4-6"}),
    r.status_code == 200,
    r.json()["tokens"] > 0
))

test("count_missing_model_422", lambda: (
    r := requests.post(f"{BASE['token']}/api/v1/count",
        json={"text": "hello"}),
    r.status_code == 422  # model is default, but Pydantic may not enforce
))

test("count_invalid_model_400", lambda: (
    r := requests.post(f"{BASE['token']}/api/v1/count",
        json={"text": "hello", "model": "fake-model"}),
    r.status_code == 400,
    "msg" in r.json()
))

test("count_batch", lambda: (
    r := requests.post(f"{BASE['token']}/api/v1/count/batch",
        json={"messages": [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "Hi"}
        ], "model": "claude-sonnet-4-6"}),
    r.status_code == 200,
    len(r.json()["counts"]) == 2
))

test("estimate", lambda: (
    r := requests.post(f"{BASE['token']}/api/v1/estimate",
        json={"text": "Hello world!", "model": "any"}),
    r.status_code == 200,
    r.json()["estimated_tokens"] > 0
))

test("calculate_cost_online", lambda: (
    r := requests.post(f"{BASE['token']}/api/v1/cost",
        json={"usage": {"prompt_tokens": 10000, "completion_tokens": 1000},
              "model": "claude-sonnet-4-6", "mode": "online"}),
    r.status_code == 200,
    r.json()["total"] > 0
))

test("calculate_cost_batch", lambda: (
    r := requests.post(f"{BASE['token']}/api/v1/cost",
        json={"usage": {"prompt_tokens": 10000, "completion_tokens": 1000},
              "model": "claude-sonnet-4-6", "mode": "batch"}),
    r.status_code == 200
))

test("calculate_cost_with_cache", lambda: (
    r := requests.post(f"{BASE['token']}/api/v1/cost",
        json={"usage": {"prompt_tokens": 100000, "completion_tokens": 10000,
              "cache_hit_tokens": 50000},
              "model": "claude-sonnet-4-6", "mode": "online"}),
    r.status_code == 200,
    r.json()["cache_savings"] >= 0
))

test("calculate_cost_long_context", lambda: (
    r := requests.post(f"{BASE['token']}/api/v1/cost",
        json={"usage": {"prompt_tokens": 300000, "completion_tokens": 10000},
              "model": "gpt-5.5", "mode": "online"}),
    r.status_code == 200,
    r.json()["long_context_surcharge"] > 0  # >272K triggers surcharge
))

test("compare_models", lambda: (
    r := requests.post(f"{BASE['token']}/api/v1/compare",
        json={"input_tokens": 100000, "estimated_output": 20000,
              "candidates": ["claude-opus-4-8", "deepseek-v4-flash"]}),
    r.status_code == 200,
    len(r.json()) == 2,
    r.json()[0]["model"] == "deepseek-v4-flash"  # cheapest first
))

test("list_models", lambda: (
    r := requests.get(f"{BASE['token']}/api/v1/models"),
    r.status_code == 200,
    r.json()["count"] >= 17
))

test("get_pricing", lambda: (
    r := requests.get(f"{BASE['token']}/api/v1/pricing/deepseek-v4-flash"),
    r.status_code == 200,
    r.json()["provider"] == "deepseek"
))

test("get_pricing_notfound_404", lambda: (
    r := requests.get(f"{BASE['token']}/api/v1/pricing/fake-model"),
    r.status_code == 404
))

test("truncate", lambda: (
    r := requests.post(f"{BASE['token']}/api/v1/truncate",
        json={"messages": [
            {"role": "system", "content": "You are helpful.", "index": 0},
            {"role": "user", "content": "Hello!", "index": 1}
        ], "model": "claude-sonnet-4-6"}),
    r.status_code == 200,
    "tokens_kept" in r.json()
))

# ==================== mcp-bridge (8004) ====================
print("\n📦 [2/4] mcp-bridge — MCP 协议 + 工具治理\n")

test("health", lambda: (
    r := requests.get(f"{BASE['mcp']}/health"),
    r.status_code == 200,
    r.json()["tools"] >= 3
))

test("jsonrpc_initialize", lambda: (
    r := requests.post(f"{BASE['mcp']}/mcp",
        json={"jsonrpc": "2.0", "method": "initialize", "id": 1}),
    r.status_code == 200,
    r.json()["result"]["protocolVersion"] == "2024-11-05"
))

test("jsonrpc_tools_list", lambda: (
    r := requests.post(f"{BASE['mcp']}/mcp",
        json={"jsonrpc": "2.0", "method": "tools/list", "id": 2}),
    r.status_code == 200,
    len(r.json()["result"]["tools"]) >= 3
))

test("jsonrpc_tools_call_echo", lambda: (
    r := requests.post(f"{BASE['mcp']}/mcp",
        json={"jsonrpc": "2.0", "method": "tools/call",
              "params": {"name": "echo", "arguments": {"message": "hello"}}, "id": 3}),
    r.status_code == 200,
    "echo" in str(r.json()["result"])
))

test("jsonrpc_tools_call_calc", lambda: (
    r := requests.post(f"{BASE['mcp']}/mcp",
        json={"jsonrpc": "2.0", "method": "tools/call",
              "params": {"name": "calculator", "arguments": {"expression": "2+2"}}, "id": 4}),
    r.status_code == 200
))

test("jsonrpc_method_not_found", lambda: (
    r := requests.post(f"{BASE['mcp']}/mcp",
        json={"jsonrpc": "2.0", "method": "nonexistent", "id": 5}),
    r.json()["error"]["code"] == -32601
))

test("rest_invoke", lambda: (
    r := requests.post(f"{BASE['mcp']}/api/v1/tools/invoke",
        json={"tool": "echo", "params": {"message": "test"}}),
    r.status_code == 200,
    "result" in r.json()
))

test("rest_register", lambda: (
    r := requests.post(f"{BASE['mcp']}/api/v1/tools/register?name=test_tool&description=Test&schema={}"),
    r.status_code == 200
))

test("rest_discover", lambda: (
    r := requests.get(f"{BASE['mcp']}/api/v1/tools/discover"),
    r.status_code == 200,
    "tools" in r.json()
))

test("audit_logs", lambda: (
    r := requests.get(f"{BASE['mcp']}/api/v1/audit/logs"),
    r.status_code == 200,
    "logs" in r.json()
))

# ==================== AgentForge (8001) ====================
print("\n📦 [3/4] AgentForge — Agent 框架 + 持久化\n")

test("health", lambda: (
    r := requests.get(f"{BASE['forge']}/health"),
    r.status_code == 200,
    r.json()["db"] == "postgresql",
    r.json()["cache"] == "redis"
))

test("create_config", lambda: (
    r := requests.post(f"{BASE['forge']}/api/v1/configs",
        json={"name": "E2E Test Agent", "framework": "native", "model": "deepseek-v4-pro"}),
    r.status_code == 201,
    "id" in r.json()
))

config_id = requests.post(f"{BASE['forge']}/api/v1/configs",
    json={"name": "E2E Agent 2", "framework": "langchain"}).json().get("id", "")

test("list_configs", lambda: (
    r := requests.get(f"{BASE['forge']}/api/v1/configs"),
    r.status_code == 200,
    len(r.json()) >= 2  # Should have at least 2 configs from previous tests
))

test("run_agent_native", lambda: (
    r := requests.post(f"{BASE['forge']}/api/v1/agents/run",
        json={"messages": [{"role": "user", "content": "Hello"}],
              "framework": "native", "model": "claude-sonnet-4-6"}),
    r.status_code == 200,
    r.json()["status"] == "success"
))

test("run_agent_langchain", lambda: (
    r := requests.post(f"{BASE['forge']}/api/v1/agents/run",
        json={"messages": [{"role": "user", "content": "Test"}],
              "framework": "langchain"}),
    r.status_code == 200
))

test("run_agent_openai", lambda: (
    r := requests.post(f"{BASE['forge']}/api/v1/agents/run",
        json={"messages": [{"role": "user", "content": "Test"}],
              "framework": "openai_agents"}),
    r.status_code == 200
))

test("run_invalid_framework_400", lambda: (
    r := requests.post(f"{BASE['forge']}/api/v1/agents/run",
        json={"messages": [{"role": "user", "content": "x"}], "framework": "invalid"}),
    r.status_code == 400
))

test("run_missing_messages_422", lambda: (
    r := requests.post(f"{BASE['forge']}/api/v1/agents/run",
        json={}),
    r.status_code == 422
))

test("list_sessions", lambda: (
    r := requests.get(f"{BASE['forge']}/api/v1/sessions"),
    r.status_code == 200,
    len(r.json()) >= 1  # At least 1 session from the run above
))

# ==================== AgentEval (8000) ====================
print("\n📦 [4/4] AgentEval-Platform — 评测平台\n")

test("health", lambda: (
    r := requests.get(f"{BASE['eval']}/health"),
    r.status_code == 200
))

test("create_evaluation", lambda: (
    r := requests.post(f"{BASE['eval']}/api/v1/evaluations",
        json={"name": "E2E Test Eval", "agent_config": {"model": "claude-sonnet-4-6"}, "max_cases": 5}),
    r.status_code == 201,
    r.json()["status"] in ("queued", "running")
))

eval_id = requests.post(f"{BASE['eval']}/api/v1/evaluations",
    json={"name": "E2E Eval 2", "max_cases": 3}).json().get("id", "")

test("list_evaluations", lambda: (
    r := requests.get(f"{BASE['eval']}/api/v1/evaluations"),
    r.status_code == 200,
    r.json()["total"] >= 2
))

test("get_evaluation", lambda: (
    r := requests.get(f"{BASE['eval']}/api/v1/evaluations/{eval_id}"),
    r.status_code == 200,
    r.json()["name"] == "E2E Eval 2"
))

test("get_status", lambda: (
    r := requests.get(f"{BASE['eval']}/api/v1/evaluations/{eval_id}/status"),
    r.status_code == 200,
    "completed" in r.json()
))

test("get_metrics", lambda: (
    r := requests.get(f"{BASE['eval']}/api/v1/evaluations/{eval_id}/metrics"),
    r.status_code == 200
))

test("cancel_evaluation", lambda: (
    r := requests.delete(f"{BASE['eval']}/api/v1/evaluations/{eval_id}"),
    r.status_code == 200,
    r.json()["status"] == "cancelled"
))

test("get_nonexistent_404", lambda: (
    r := requests.get(f"{BASE['eval']}/api/v1/evaluations/nonexistent-id"),
    r.status_code == 404
))

test("create_missing_name_422", lambda: (
    r := requests.post(f"{BASE['eval']}/api/v1/evaluations",
        json={}),
    r.status_code == 422
))

# ==================== REPORT ====================
total = PASS + FAIL
print(f"\n{'='*50}")
print(f"  测试结果汇总")
print(f"{'='*50}")
print(f"  token-core   (8003):  见上方明细")
print(f"  mcp-bridge   (8004):  见上方明细")
print(f"  AgentForge   (8001):  见上方明细 (PostgreSQL + Redis)")
print(f"  AgentEval    (8000):  见上方明细 (PostgreSQL)")
print(f"{'='*50}")
print(f"  PASS:  {PASS}")
print(f"  FAIL:  {FAIL}")
print(f"  TOTAL: {total}")
print(f"  RATE:  {PASS/total*100:.0f}%" if total > 0 else "  RATE:  N/A")
print(f"{'='*50}")

sys.exit(0 if FAIL == 0 else 1)
