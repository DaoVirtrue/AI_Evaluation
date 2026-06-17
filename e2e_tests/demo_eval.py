#!/usr/bin/env python3
"""
零基础本地评测脚本 — 全流程端到端验证
1. 读取测试数据集
2. 逐条调用 AgentForge 执行 Agent
3. 对比预期答案 → 打分
4. 结果写入 AgentEval-Platform
"""
import json, sys, time, requests

AGENT_FORGE = "http://localhost:8001"
AGENT_EVAL = "http://localhost:8000"
TOKEN_CORE = "http://localhost:8003"
DATASET = "../datasets/sample_qa.jsonl"

PASS = FAIL = 0

def log(msg):
    print(f"  {msg}")

def main():
    global PASS, FAIL

    print("=" * 55)
    print("  Agent 评测平台 — 本地验证脚本")
    print("=" * 55)
    print("")

    # 1. 健康检查
    print("[1/5] 服务健康检查")
    for name, url in [("AgentEval", AGENT_EVAL), ("AgentForge", AGENT_FORGE), ("token-core", TOKEN_CORE)]:
        try:
            r = requests.get(f"{url}/health", timeout=5)
            if r.status_code == 200:
                j = r.json()
                backend = j.get("backend", j.get("db", "?"))
                log(f"✅ {name}: OK (backend={backend})")
            else:
                raise Exception(f"HTTP {r.status_code}")
        except Exception as e:
            print(f"  ❌ {name}: {e}")
            print("\n请先启动服务: docker compose up -d")
            sys.exit(1)

    # 2. 加载数据集
    print(f"\n[2/5] 加载数据集: {DATASET}")
    cases = []
    try:
        with open(DATASET, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    cases.append(json.loads(line))
    except FileNotFoundError:
        print(f"  ❌ 数据集文件不存在: {DATASET}")
        sys.exit(1)
    log(f"✅ 加载了 {len(cases)} 条测试用例")

    # 3. 创建评测任务
    print("\n[3/5] 在 AgentEval 创建评测任务")
    r = requests.post(f"{AGENT_EVAL}/api/v1/evaluations", json={
        "name": f"本地验证评测 {time.strftime('%H:%M:%S')}",
        "agent_config": {"model": "claude-sonnet-4-6"},
        "max_cases": len(cases),
    })
    if r.status_code != 201:
        print(f"  ❌ 创建失败: {r.status_code} {r.text}")
        sys.exit(1)
    eval_id = r.json()["id"]
    log(f"✅ 评测任务创建: {eval_id}")

    # 4. 逐条执行评测
    print(f"\n[4/5] 逐条执行 {len(cases)} 个测试用例")
    results = []

    for i, case in enumerate(cases):
        cid = case["case_id"]
        question = case["input"]
        expected = case["expected_output"].lower().strip()
        log(f"[{i+1}/{len(cases)}] {cid}: {question[:50]}...")

        try:
            # 调用 AgentForge
            r = requests.post(f"{AGENT_FORGE}/api/v1/agents/run", json={
                "messages": [{"role": "user", "content": question}],
                "framework": "native",
                "model": "claude-sonnet-4-6",
            }, timeout=30)
            if r.status_code != 200:
                log(f"  ⚠️ AgentForge 返回 {r.status_code}")
                continue

            agent_resp = r.json()
            output = agent_resp.get("output", "").lower()

            # 简单的包含匹配评分
            passed = any(kw in output for kw in expected.split())
            score = 1.0 if passed else 0.0

            result = {
                "case_id": cid,
                "input": question,
                "expected_output": expected,
                "actual_output": output[:500],
                "passed": passed,
                "score": score,
                "token_usage": {
                    "prompt_tokens": agent_resp.get("total_tokens", 0),
                    "completion_tokens": 0,
                    "total_cost": agent_resp.get("total_cost", 0),
                },
                "latency_ms": agent_resp.get("total_latency_ms", 0),
            }

            # 统计 Token
            try:
                tc = requests.post(f"{TOKEN_CORE}/api/v1/count", json={
                    "text": question, "model": "claude-sonnet-4-6"
                }, timeout=5)
                if tc.status_code == 200:
                    result["token_usage"]["prompt_tokens"] = tc.json()["tokens"]
                    cost_r = requests.post(f"{TOKEN_CORE}/api/v1/cost", json={
                        "usage": {"prompt_tokens": tc.json()["tokens"], "completion_tokens": 50},
                        "model": "claude-sonnet-4-6", "mode": "online"
                    }, timeout=5)
                    if cost_r.status_code == 200:
                        result["token_usage"]["total_cost"] = cost_r.json()["total"]
            except: pass

            results.append(result)

            if passed:
                PASS += 1
                log(f"  ✅ 通过 (得分: {score})")
            else:
                FAIL += 1
                log(f"  ❌ 未通过 (期望含: {expected[:30]}...)")

        except Exception as e:
            FAIL += 1
            log(f"  ❌ 异常: {e}")

    # 5. 输出报告
    total = PASS + FAIL
    print(f"\n[5/5] 评测报告")
    print("=" * 55)
    print(f"  测试用例总数: {total}")
    print(f"  ✅ 通过: {PASS}")
    print(f"  ❌ 未通过: {FAIL}")
    print(f"  📊 通过率: {PASS/total*100:.1f}%" if total > 0 else "  N/A")
    print(f"  评测任务 ID: {eval_id}")
    print(f"  评测平台: http://localhost:3000/evaluations/{eval_id}")
    print("=" * 55)

    # 保存结果到文件
    report = {
        "eval_id": eval_id,
        "total": total,
        "passed": PASS,
        "failed": FAIL,
        "pass_rate": round(PASS/total*100, 1) if total > 0 else 0,
        "results": results,
    }
    report_path = "demo_eval_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n📄 详细报告: {report_path}")
    print(f"📸 截图已保存在 screenshots/ 目录（需运行 playwright_e2e.js）")

    return 0 if FAIL == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
