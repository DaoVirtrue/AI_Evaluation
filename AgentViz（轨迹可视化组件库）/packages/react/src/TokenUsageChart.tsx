import React from "react";
import type { TrajectoryStep } from "@agent-viz/transform";
import { ErrorBoundary, EmptyState } from "./shared";

export interface TokenUsageChartProps {
  steps: TrajectoryStep[];
  height?: number;
  width?: number | string;
}

export function TokenUsageChart({ steps, height = 300, width = "100%" }: TokenUsageChartProps) {
  const data = steps.filter((s) => s.tokenUsage);
  if (data.length === 0) return <EmptyState icon="📈" title="暂无 Token 数据" />;

  const maxTokens = Math.max(...data.map((s) => (s.tokenUsage?.promptTokens || 0) + (s.tokenUsage?.completionTokens || 0)), 1);
  const totalCost = data.reduce((sum, s) => sum + (s.tokenUsage?.cost || 0), 0);

  return (
    <ErrorBoundary>
      <div style={{ padding: 16 }}>
        <div style={{ marginBottom: 8, fontSize: 14, color: "#6b7280" }}>
          总消耗: <strong>{data.reduce((s, d) => s + (d.tokenUsage?.promptTokens || 0) + (d.tokenUsage?.completionTokens || 0), 0).toLocaleString()}</strong> tokens
          {" · "}💰 <strong>${totalCost.toFixed(6)}</strong>
        </div>
        <div style={{ height, width, overflowY: "auto" }}>
          {data.map((step, i) => {
            const prompt = step.tokenUsage!.promptTokens;
            const completion = step.tokenUsage!.completionTokens;
            const total = prompt + completion;
            const pct = (total / maxTokens) * 100;
            return (
              <div key={i} style={{ display: "flex", alignItems: "center", marginBottom: 4 }}>
                <span style={{ fontSize: 11, width: 40 }}>#{step.index + 1}</span>
                <div style={{ flex: 1, height: 16, background: "#f3f4f6", borderRadius: 4, overflow: "hidden", display: "flex" }}>
                  <div style={{ width: `${(prompt / total) * pct}%`, background: "#3b82f6", height: "100%", transition: "width 0.3s" }} title={`Prompt: ${prompt.toLocaleString()}`} />
                  <div style={{ width: `${(completion / total) * pct}%`, background: "#22c55e", height: "100%" }} title={`Completion: ${completion.toLocaleString()}`} />
                </div>
                <span style={{ fontSize: 11, width: 60, textAlign: "right", color: "#6b7280" }}>{total.toLocaleString()}tk</span>
              </div>
            );
          })}
        </div>
      </div>
    </ErrorBoundary>
  );
}
