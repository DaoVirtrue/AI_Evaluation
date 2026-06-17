---
description: Estimate token count and cost for selected code/config
argument-hint: <file-path>
---

## Task: Token Estimation

1. Read file at `$1`
2. Call token-core API: `POST http://localhost:8003/api/v1/count`
3. Call token-core API: `POST http://localhost:8003/api/v1/compare` with top 5 models
4. Output: tokens, estimated cost per model, recommendation
