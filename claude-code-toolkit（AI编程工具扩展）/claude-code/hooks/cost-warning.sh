#!/bin/bash
BUDGET=${BUDGET:-5.00}
ESTIMATED_COST=$(curl -s http://localhost:8003/api/v1/cost -d '{"usage":{"prompt_tokens":0,"completion_tokens":0},"model":"claude-sonnet-4-6"}' 2>/dev/null || echo "0")
if (( $(echo "$ESTIMATED_COST > $BUDGET" | bc -l 2>/dev/null || echo 0) )); then
    echo "💰 COST WARNING: Estimated session cost exceeds budget ($$BUDGET)"
fi
