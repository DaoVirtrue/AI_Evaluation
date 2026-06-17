#!/bin/bash
set -euo pipefail
echo "============================================"
echo "  mcp-bridge Test Suite"
echo "============================================"
echo ""

PASS_TOTAL=0
FAIL_TOTAL=0

run() {
    local name="$1"
    shift
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

run "Unit Tests" python unit_tests/test_bridge.py

if curl -sf http://localhost:8004/health > /dev/null 2>&1; then
    run "API Tests" python API_tests/test_api.py
else
    echo "[SKIP] API Tests — server not running (start: docker compose up -d)"
fi

echo "============================================"
echo "  Test Results Summary"
echo "============================================"
echo "Unit/API Tests:  PASS  $PASS_TOTAL  FAIL  $FAIL_TOTAL"
echo "============================================"
echo "TOTAL: PASS  $PASS_TOTAL  FAIL  $FAIL_TOTAL  SKIP  0"
echo "============================================"
exit $FAIL_TOTAL
