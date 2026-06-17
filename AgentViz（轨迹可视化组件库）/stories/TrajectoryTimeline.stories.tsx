import React from "react";
import type { Meta, StoryObj } from "@storybook/react";
import { TrajectoryTimeline } from "../packages/react/src/TrajectoryTimeline";
import type { TrajectoryStep } from "../packages/transform/src";

const meta: Meta<typeof TrajectoryTimeline> = {
  title: "AgentViz/TrajectoryTimeline",
  component: TrajectoryTimeline,
};
export default meta;

const sampleSteps: TrajectoryStep[] = [
  { index: 0, type: "llm_call", timestamp: "2026-06-16T10:00:00Z", model: "claude-sonnet-4-6", latencyMs: 1200, tokenUsage: { promptTokens: 500, completionTokens: 200, cost: 0.003 } },
  { index: 1, type: "tool_call", timestamp: "2026-06-16T10:00:01Z", toolName: "web_search", toolInput: { query: "test" }, latencyMs: 350, tokenUsage: { promptTokens: 100, completionTokens: 50, cost: 0.0005 } },
  { index: 2, type: "llm_call", timestamp: "2026-06-16T10:00:02Z", model: "claude-sonnet-4-6", latencyMs: 900, tokenUsage: { promptTokens: 800, completionTokens: 300, cost: 0.005 } },
  { index: 3, type: "output", timestamp: "2026-06-16T10:00:03Z" },
];

export const Default: StoryObj = {
  args: { steps: sampleSteps, height: 400 },
};

export const Empty: StoryObj = {
  args: { steps: [], height: 400 },
};

export const ManySteps: StoryObj = {
  args: {
    steps: Array.from({ length: 1000 }, (_, i) => ({
      index: i,
      type: i % 5 === 0 ? "tool_call" : i % 3 === 0 ? "thinking" : "llm_call",
      timestamp: new Date().toISOString(),
      latencyMs: Math.random() * 2000,
    } as TrajectoryStep)),
    height: 600,
    renderMode: "canvas" as const,
  },
};
