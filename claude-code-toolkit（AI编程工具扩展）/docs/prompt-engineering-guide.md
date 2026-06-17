# Prompt Engineering Guide

## 1. Structured Prompt Principles
- **Layered Design**: System → Context → Task → Constraints → Output Format
- **Clear Boundaries**: Use XML tags to separate user input from system instructions
- **Example-Driven**: Provide 2-3 input/output examples
- **Explicit Constraints**: Never say "don't do X", say "if X happens, do Y"

## 2. Agent Debugging Patterns
- **Step-by-Step Diagnosis**: Start from failure point, work backwards
- **State Snapshot**: Full Context Window state at failure is key
- **Hypothesis-Driven**: Formulate → Modify → Re-run → Verify

## 3. Cost Optimization
- Reduce redundant descriptions
- Use structured output (JSON/XML) to reduce tokens
- Cache reusable system prompt fragments
- Use cheaper models for simple classification tasks

## 4. Model Selection Guide (2026 Q2)
See token-core pricing table for real-time data.
Quick reference: simple→Haiku($1), medium→Sonnet($3), complex→Opus($5), extreme→Fable($10)
