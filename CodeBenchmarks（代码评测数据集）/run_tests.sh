#!/bin/bash
# CodeBenchmarks — Test Runner
set -euo pipefail

PASS=0
FAIL=0

echo "=========================================="
echo "CodeBenchmarks Test Suite"
echo "=========================================="

echo ""
echo "--- Unit Tests ---"
if python unit_tests/test_benchmarks.py; then
    echo "✓ Unit tests passed"
    PASS=$((PASS + 1))
else
    echo "✗ Unit tests failed"
    FAIL=$((FAIL + 1))
fi

echo ""
echo "=========================================="
echo "Results: $PASS passed, $FAIL failed"
echo "=========================================="

exit $FAIL
