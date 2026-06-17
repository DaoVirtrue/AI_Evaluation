#!/bin/bash
set -euo pipefail
echo "============================================"; echo "  agent-container-service Tests"
echo "============================================"
P=0; F=0
run() { local n="$1"; shift; echo "--- $n ---"; if "$@"; then echo "[PASS] $n"; P=$((P+1)); else echo "[FAIL] $n"; F=$((F+1)); fi; echo ""; }
run "Docker Compose Config Check" docker compose -f docker-compose/docker-compose.dev.yml config > /dev/null 2>&1
run "Helm Lint" helm lint k8s/helm-chart 2>&1 || echo "Helm not installed, skipped"
run "Prometheus Config" promtool check config monitoring/prometheus/prometheus.yml 2>&1 || echo "promtool not installed, skipped"
echo "============================================"; echo "Results: PASS $P FAIL $F"; exit $F
