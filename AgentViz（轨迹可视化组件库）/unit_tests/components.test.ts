import { describe, it, expect } from "vitest";
import { normalize, aggregate } from "../packages/transform/src";

describe("normalize", () => {
  it("handles empty array", () => {
    expect(normalize([])).toEqual([]);
  });

  it("normalizes agentforge format", () => {
    const raw = [
      { step_type: "llm_call", timestamp: "2026-01-01", model: "test", input: "hello", output: "world", latency_ms: 100, token_usage: { prompt_tokens: 10, completion_tokens: 5, total_cost: 0.001 } },
    ];
    const result = normalize(raw);
    expect(result).toHaveLength(1);
    expect(result[0].type).toBe("llm_call");
    expect(result[0].tokenUsage?.cost).toBe(0.001);
  });

  it("normalizes tool calls", () => {
    const raw = [{ step_type: "tool_call", tool_name: "search", tool_input: { q: "test" }, latency_ms: 200 }];
    const result = normalize(raw);
    expect(result[0].type).toBe("tool_call");
    expect(result[0].toolName).toBe("search");
  });
});

describe("aggregate", () => {
  it("computes correct stats", () => {
    const steps = [
      { index: 0, type: "llm_call" as const, timestamp: "", tokenUsage: { promptTokens: 100, completionTokens: 50, cost: 0.01 }, latencyMs: 1000 },
      { index: 1, type: "tool_call" as const, timestamp: "", latencyMs: 500 },
      { index: 2, type: "llm_call" as const, timestamp: "", tokenUsage: { promptTokens: 200, completionTokens: 100, cost: 0.02 }, latencyMs: 1500 },
    ];
    const stats = aggregate(steps);
    expect(stats.totalSteps).toBe(3);
    expect(stats.llmCalls).toBe(2);
    expect(stats.toolCalls).toBe(1);
    expect(stats.totalTokens).toBe(450);
    expect(stats.totalCost).toBeCloseTo(0.03, 4);
    expect(stats.totalLatencyMs).toBe(3000);
  });

  it("handles empty", () => {
    const stats = aggregate([]);
    expect(stats.totalSteps).toBe(0);
  });
});
