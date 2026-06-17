#!/bin/bash
set -euo pipefail
echo "============================================"; echo "  AgentForge Test Suite"; echo "============================================"
P=0; F=0
run() { local n="$1"; shift; echo "--- $n ---"; if "$@"; then echo "[PASS] $n"; P=$((P+1)); else echo "[FAIL] $n"; F=$((F+1)); fi; echo ""; }
run "Unit Tests" python unit_tests/test_agents.py
if curl -sf http://localhost:8001/health > /dev/null 2>&1; then run "API Tests" python API_tests/test_api.py
else echo "[SKIP] API Tests — server not running (docker compose up -d)"; fi
echo "============================================"; echo "  Results: PASS  $P  FAIL  $F"
echo "============================================"; exit $F
