#!/bin/bash
# CodeSandbox — Test Runner
set -euo pipefail

PASS=0
FAIL=0

echo "=========================================="
echo "CodeSandbox Test Suite"
echo "=========================================="

# Unit Tests
echo ""
echo "--- Unit Tests ---"
if python unit_tests/test_sandbox.py; then
    echo "✓ Unit tests passed"
    PASS=$((PASS + 1))
else
    echo "✗ Unit tests failed"
    FAIL=$((FAIL + 1))
fi

# API Tests (only if server is running)
echo ""
echo "--- API Tests ---"
if curl -sf http://localhost:8005/health > /dev/null 2>&1; then
    if python API_tests/test_api.py; then
        echo "✓ API tests passed"
        PASS=$((PASS + 1))
    else
        echo "✗ API tests failed"
        FAIL=$((FAIL + 1))
    fi
else
    echo "⚠ API tests skipped (server not running on port 8005)"
fi

echo ""
echo "=========================================="
echo "Results: $PASS passed, $FAIL failed"
echo "=========================================="

exit $FAIL
