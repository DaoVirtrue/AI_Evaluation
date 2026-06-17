#!/bin/bash
set -euo pipefail
echo "============================================"; echo "  claude-code-toolkit Tests"; echo "============================================"
P=0; F=0
run() { local n="$1"; shift; echo "--- $n ---"; if "$@"; then echo "[PASS] $n"; P=$((P+1)); else echo "[FAIL] $n"; F=$((F+1)); fi; echo ""; }
run "Hooks: pre-tool-use syntax" bash -n claude-code/hooks/pre-tool-use.sh
run "Hooks: cost-warning syntax" bash -n claude-code/hooks/cost-warning.sh
run "Prompts: template count" [ $(find prompts -name "*.md" | wc -l) -ge 2 ]
run "Docs: guide exists" [ -f docs/prompt-engineering-guide.md ]
echo "============================================"; echo "Results: PASS $P FAIL $F"; exit $F
