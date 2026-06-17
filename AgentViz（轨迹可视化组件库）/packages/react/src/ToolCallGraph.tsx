import React from "react";
import type { TrajectoryStep } from "@agent-viz/transform";
import { ErrorBoundary, EmptyState } from "./shared";

export interface ToolCallGraphProps {
  steps: TrajectoryStep[];
}

export function ToolCallGraph({ steps }: ToolCallGraphProps) {
  const tools = steps.filter((s) => s.type === "tool_call");
  if (tools.length === 0) return <EmptyState icon="🔧" title="无工具调用" />;

  return (
    <ErrorBoundary>
      <div style={{ padding: 16 }}>
        <svg width="100%" height={Math.max(tools.length * 60, 120)}>
          {tools.map((step, i) => (
            <g key={i}>
              <rect x={20} y={i * 60 + 10} width={200} height={40} rx={6} fill={step.toolError ? "#fef2f2" : "#f0fdf4"} stroke={step.toolError ? "#fca5a5" : "#86efac"} />
              <text x={30} y={i * 60 + 35} fontSize={13} fill="#374151">
                {step.toolName || `Tool #${i + 1}`}
              </text>
              {step.toolError && <text x={30} y={i * 60 + 55} fontSize={10} fill="#dc2626">{step.toolError}</text>}
              {step.latencyMs != null && (
                <text x={230} y={i * 60 + 35} fontSize={11} fill="#9ca3af">{step.latencyMs}ms</text>
              )}
              {i < tools.length - 1 && <line x1={120} y1={i * 60 + 50} x2={120} y2={(i + 1) * 60 + 10} stroke="#d1d5db" strokeWidth={1} />}
            </g>
          ))}
        </svg>
      </div>
    </ErrorBoundary>
  );
}
