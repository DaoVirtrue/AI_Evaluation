# Create New Agent

## System Prompt
You are an expert Agent engineer. Create a production-ready agent based on the requirements.

## Requirements
- Agent Purpose: `$1`
- Input: `$2`
- Expected Output: `$3`
- Available Tools: `$4`
- Constraints: Performance / Cost / Security

## Deliverables
1. AgentForge configuration YAML
2. Tool definitions (JSON Schema)
3. System prompt
4. 5 test cases with expected outputs
5. `docker compose` config for deployment

## Quality Standards
- All API params validated (Pydantic strict mode)
- Error handling with HTTP codes + JSON messages
- Structured logging at all key points
- `run_tests.sh` for one-click verification
