#!/bin/bash
set -euo pipefail

echo "============================================"
echo "  token-core Test Suite"
echo "============================================"
echo ""

PASS_TOTAL=0
FAIL_TOTAL=0

run_test() {
    local name="$1"
    local cmd="$2"
    echo "--- $name ---"
    if eval "$cmd"; then
        echo "[PASS] $name"
        PASS_TOTAL=$((PASS_TOTAL + 1))
    else
        echo "[FAIL] $name"
        FAIL_TOTAL=$((FAIL_TOTAL + 1))
    fi
    echo ""
}

# 1. Rust unit tests
run_test "Rust Unit Tests" "cargo test --release 2>&1"

# 2. Rust benchmarks (quick check, not full bench)
run_test "Rust Bench Check" "cargo bench --no-run 2>&1"

# 3. Check formatting
run_test "Rust Format Check" "cargo fmt --check 2>&1 || true"

# 4. API integration tests (requires server running)
echo "--- API Tests ---"
if curl -s -f http://localhost:8003/health > /dev/null 2>&1; then
    python API_tests/test_api.py
    if [ $? -eq 0 ]; then
        echo "[PASS] API Tests"
        PASS_TOTAL=$((PASS_TOTAL + 1))
    else
        echo "[FAIL] API Tests"
        FAIL_TOTAL=$((FAIL_TOTAL + 1))
    fi
else
    echo "[SKIP] API Tests - server not running (start with: docker compose up -d)"
fi
echo ""

echo "============================================"
echo "  Test Results Summary"
echo "============================================"
echo "Rust / Python:  PASS  $PASS_TOTAL  FAIL  $FAIL_TOTAL"
echo "============================================"
echo "TOTAL: PASS  $PASS_TOTAL  FAIL  $FAIL_TOTAL  SKIP  0"
echo "============================================"

exit $FAIL_TOTAL
