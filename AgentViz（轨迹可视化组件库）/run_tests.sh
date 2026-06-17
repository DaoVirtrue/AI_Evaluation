#!/bin/bash
set -euo pipefail
echo "============================================"
echo "  AgentViz Test Suite"
echo "============================================"

PASS_TOTAL=0
FAIL_TOTAL=0

run() { local n="$1"; shift; echo "--- $n ---"; if "$@"; then echo "[PASS] $n"; PASS_TOTAL=$((PASS_TOTAL+1)); else echo "[FAIL] $n"; FAIL_TOTAL=$((FAIL_TOTAL+1)); fi; echo ""; }

if command -v pnpm &>/dev/null; then
  run "Unit Tests" pnpm test
  run "Type Check" pnpm run build 2>&1 || true
else
  echo "[SKIP] pnpm not installed — install Node.js 22+ and run: npm install -g pnpm"
fi

echo "============================================"
echo "  Test Results Summary"
echo "============================================"
echo "Unit Tests:      PASS  $PASS_TOTAL  FAIL  $FAIL_TOTAL"
echo "============================================"
exit $FAIL_TOTAL
