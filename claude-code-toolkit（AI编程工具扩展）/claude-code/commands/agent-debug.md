---
description: Debug a failed agent evaluation case
argument-hint: <evaluation-id> <case-id>
---

## Task: Debug Failed Agent Case

1. Fetch trajectory: `GET http://localhost:8000/api/v1/evaluations/$1/trajectory/$2`
2. Display each step with token usage and tool calls
3. Identify failure point:
   - Tool call error? → Suggest fix
   - Context overflow? → Suggest truncation strategy
   - Wrong reasoning? → Suggest prompt improvement
4. Apply fix and re-run to verify
