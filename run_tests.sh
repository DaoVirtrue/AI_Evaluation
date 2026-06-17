#!/bin/bash
# 统一测试入口 — 满足硬性要求：一键执行全部测试
set -euo pipefail

PASS_TOTAL=0
FAIL_TOTAL=0

run() {
    local name="$1"; shift
    echo "--- $name ---"
    if "$@"; then
        echo "[PASS] $name"
        PASS_TOTAL=$((PASS_TOTAL + 1))
    else
        echo "[FAIL] $name"
        FAIL_TOTAL=$((FAIL_TOTAL + 1))
    fi
    echo ""
}

echo "============================================"
echo "  Agent 全栈平台 — 统一测试套件"
echo "  Unit Tests + API Tests + E2E Tests"
echo "============================================"
echo ""

# ===== Unit Tests =====
echo "📦 [1/4] 单元测试 (Unit Tests)"
echo ""

if command -v python &>/dev/null; then
    for f in */unit_tests/*.py; do
        if [ -f "$f" ]; then
            run "$(basename $(dirname $(dirname $f)))/$(basename $f)" python "$f"
        fi
    done
else
    echo "[SKIP] Python not available in this shell (tests run in Docker)"
fi

# ===== API Tests =====
echo "📦 [2/4] API 接口测试 (API Tests)"
echo ""

if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
    # Use Docker to run API tests
    run "token-core API" docker exec agent-token-core-1 python -c "
import requests, json
r = requests.get('http://localhost:8003/health')
assert r.json()['status'] == 'ok'
r = requests.post('http://localhost:8003/api/v1/count', json={'text':'Hello','model':'claude-sonnet-4-6'})
assert r.json()['tokens'] > 0
print('token-core API: OK')
" 2>&1 || echo "[FALLBACK] token-core API tests skipped"

    run "mcp-bridge API" docker exec agent-mcp-bridge-1 python -c "
import requests
r = requests.post('http://localhost:8004/mcp', json={'jsonrpc':'2.0','method':'tools/list','id':1})
assert 'tools' in str(r.json()['result'])
print('mcp-bridge API: OK')
" 2>&1 || echo "[FALLBACK] mcp-bridge API tests skipped"

    run "AgentForge API" docker exec agent-agent-forge-1 python -c "
import requests
r = requests.get('http://localhost:8001/health')
assert r.json()['db'] == 'postgresql'
print('AgentForge API: OK')
" 2>&1 || echo "[FALLBACK] AgentForge API tests skipped"

    run "AgentEval API" docker exec agent-agent-eval-api-1 python -c "
import requests
r = requests.get('http://localhost:8000/health')
assert r.json()['status'] == 'ok'
print('AgentEval API: OK')
" 2>&1 || echo "[FALLBACK] AgentEval API tests skipped"
else
    echo "[SKIP] Services not running (start: docker compose up -d)"
fi

# ===== E2E Demo =====
echo "📦 [3/4] 端到端评测验证 (Demo Eval)"
echo ""

if curl -sf http://localhost:8000/health > /dev/null 2>&1 && command -v python &>/dev/null; then
    run "demo_eval" python e2e_tests/demo_eval.py 2>&1 || true
elif command -v docker &>/dev/null && docker ps | grep -q agent-forge; then
    echo "[INFO] Running demo_eval via Docker..."
    docker cp e2e_tests/demo_eval.py agent-agent-forge-1:/app/demo_eval.py 2>/dev/null
    docker cp datasets/sample_qa.jsonl agent-agent-forge-1:/app/sample_qa.jsonl 2>/dev/null
    run "demo_eval (Docker)" docker exec agent-agent-forge-1 python /app/demo_eval.py 2>&1 || true
else
    echo "[SKIP] Cannot run demo_eval"
fi

# ===== E2E Playwright =====
echo "📦 [4/4] 浏览器端到端测试 (Playwright)"
echo ""

if [ -f "e2e_tests/node_modules/.package-lock.json" ] || [ -d "e2e_tests/node_modules/playwright" ]; then
    run "playwright_e2e" node e2e_tests/playwright_e2e.js 2>&1 || true
else
    echo "[SKIP] Playwright not installed (cd e2e_tests && npm install && npx playwright install chromium)"
fi

# ===== Report =====
TOTAL=$((PASS_TOTAL + FAIL_TOTAL))
echo ""
echo "============================================"
echo "  测试结果汇总"
echo "============================================"
echo "  PASS:  $PASS_TOTAL"
echo "  FAIL:  $FAIL_TOTAL"
echo "  TOTAL: $TOTAL"
[ $TOTAL -gt 0 ] && echo "  RATE:  $(( PASS_TOTAL * 100 / TOTAL ))%"
echo "============================================"

exit $FAIL_TOTAL
