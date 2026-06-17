/**
 * @agent-viz/transform — Data normalization & aggregation
 * Web Worker-friendly: all functions are pure, no DOM access
 */

export type StepType = "llm_call" | "tool_call" | "thinking" | "output" | "error";

export interface TrajectoryStep {
  index: number;
  type: StepType;
  timestamp: string;
  model?: string;
  llmInput?: string;
  llmOutput?: string;
  toolName?: string;
  toolInput?: Record<string, unknown>;
  toolOutput?: unknown;
  toolError?: string;
  tokenUsage?: {
    promptTokens: number;
    completionTokens: number;
    thinkingTokens?: number;
    cacheHitTokens?: number;
    cost: number;
  };
  latencyMs?: number;
}

export interface TrajectoryStats {
  totalSteps: number;
  llmCalls: number;
  toolCalls: number;
  errors: number;
  totalTokens: number;
  totalCost: number;
  totalLatencyMs: number;
  stepsByType: Record<StepType, number>;
}

/**
 * Normalize raw trajectory data from different agent frameworks
 */
export function normalize(
  raw: unknown[],
  source: "agentforge" | "langchain" | "openai" = "agentforge"
): TrajectoryStep[] {
  if (!Array.isArray(raw)) return [];

  return raw.map((step: any, i: number) => {
    const base: TrajectoryStep = {
      index: i,
      type: mapStepType(step.step_type || step.type),
      timestamp: step.timestamp || new Date().toISOString(),
    };

    if (step.model) base.model = step.model;
    if (step.input) base.llmInput = typeof step.input === "string" ? step.input : JSON.stringify(step.input);
    if (step.output) base.llmOutput = typeof step.output === "string" ? step.output : JSON.stringify(step.output);
    if (step.tool_name) base.toolName = step.tool_name;
    if (step.tool_input) base.toolInput = step.tool_input;
    if (step.latency_ms) base.latencyMs = step.latency_ms;

    if (step.token_usage) {
      base.tokenUsage = {
        promptTokens: step.token_usage.prompt_tokens || 0,
        completionTokens: step.token_usage.completion_tokens || 0,
        thinkingTokens: step.token_usage.thinking_tokens,
        cacheHitTokens: step.token_usage.cache_hit_tokens,
        cost: step.token_usage.total_cost || 0,
      };
    }

    return base;
  });
}

function mapStepType(type: string): StepType {
  const map: Record<string, StepType> = {
    llm_call: "llm_call",
    tool_call: "tool_call",
    thinking: "thinking",
    output: "output",
    error: "error",
  };
  return map[type] || "llm_call";
}

/**
 * Aggregate trajectory steps into summary statistics
 */
export function aggregate(steps: TrajectoryStep[]): TrajectoryStats {
  const stats: TrajectoryStats = {
    totalSteps: steps.length,
    llmCalls: 0,
    toolCalls: 0,
    errors: 0,
    totalTokens: 0,
    totalCost: 0,
    totalLatencyMs: 0,
    stepsByType: { llm_call: 0, tool_call: 0, thinking: 0, output: 0, error: 0 },
  };

  for (const step of steps) {
    stats.stepsByType[step.type]++;
    if (step.type === "llm_call") stats.llmCalls++;
    if (step.type === "tool_call") stats.toolCalls++;
    if (step.type === "error") stats.errors++;
    if (step.tokenUsage) {
      stats.totalTokens += step.tokenUsage.promptTokens + step.tokenUsage.completionTokens;
      stats.totalCost += step.tokenUsage.cost;
    }
    if (step.latencyMs) stats.totalLatencyMs += step.latencyMs;
  }

  return stats;
}
