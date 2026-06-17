---
description: Run agent evaluation against a test dataset
argument-hint: <agent-config-path> <dataset-id>
---

## Task: Run Agent Evaluation

1. Read agent config from `$1`
2. Call AgentEval-Platform API: `POST http://localhost:8000/api/v1/evaluations`
   Body: `{"name": "Auto Eval", "agent_config": <config>, "max_cases": 10}`
3. Poll `GET /api/v1/evaluations/{id}/status` every 5s until done
4. Report: pass rate, avg latency, total cost, trajectory link
