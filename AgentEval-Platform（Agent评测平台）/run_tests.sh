#!/bin/bash
set -euo pipefail
echo "============================================"; echo "  AgentEval-Platform Test Suite"; echo "============================================"
P=0; F=0
run() { local n="$1"; shift; echo "--- $n ---"; if "$@"; then echo "[PASS] $n"; P=$((P+1)); else echo "[FAIL] $n"; F=$((F+1)); fi; echo ""; }
cd backend && run "Unit Tests" python ../unit_tests/test_models.py; cd ..
if curl -sf http://localhost:8000/health > /dev/null 2>&1; then run "API Tests" python API_tests/test_eval_api.py
else echo "[SKIP] API Tests — server not running"; fi
echo "============================================"; echo "  Results: PASS  $P  FAIL  $F"; echo "============================================"; exit $F
