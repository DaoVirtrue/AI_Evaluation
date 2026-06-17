import React from "react";
import { ErrorBoundary, EmptyState } from "./shared";

export interface ContextWindowViewerProps {
  contextLimit: number;
  usedTokens: number;
  systemTokens?: number;
  userTokens?: number;
  assistantTokens?: number;
  toolTokens?: number;
  truncated?: boolean;
}

export function ContextWindowViewer({
  contextLimit,
  usedTokens,
  systemTokens = 0,
  userTokens = 0,
  assistantTokens = 0,
  toolTokens = 0,
  truncated = false,
}: ContextWindowViewerProps) {
  const pct = Math.min((usedTokens / contextLimit) * 100, 100);
  const isWarning = pct > 80;
  const isCritical = pct > 95;

  const segments = [
    { label: "System", tokens: systemTokens, color: "#6366f1" },
    { label: "User", tokens: userTokens, color: "#3b82f6" },
    { label: "Assistant", tokens: assistantTokens, color: "#22c55e" },
    { label: "Tool", tokens: toolTokens, color: "#f59e0b" },
  ].filter((s) => s.tokens > 0);

  if (contextLimit === 0) return <EmptyState icon="🪟" title="无 Context Window 数据" />;

  return (
    <ErrorBoundary>
      <div style={{ padding: 16 }}>
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4, fontSize: 13 }}>
          <span>Context Window: {usedTokens.toLocaleString()} / {contextLimit.toLocaleString()} tokens</span>
          <span style={{ color: isCritical ? "#ef4444" : isWarning ? "#f59e0b" : "#22c55e" }}>
            {pct.toFixed(1)}%
          </span>
        </div>
        <div style={{ height: 24, background: "#f3f4f6", borderRadius: 6, overflow: "hidden", display: "flex" }}>
          {segments.map((seg, i) => (
            <div
              key={i}
              style={{ width: `${(seg.tokens / contextLimit) * 100}%`, background: seg.color, height: "100%", minWidth: 2 }}
              title={`${seg.label}: ${seg.tokens.toLocaleString()} tokens`}
            />
          ))}
        </div>
        <div style={{ display: "flex", gap: 12, marginTop: 6, fontSize: 11, flexWrap: "wrap" }}>
          {segments.map((seg, i) => (
            <span key={i} style={{ display: "flex", alignItems: "center", gap: 4 }}>
              <span style={{ width: 8, height: 8, borderRadius: 2, background: seg.color, display: "inline-block" }} />
              {seg.label}: {seg.tokens.toLocaleString()}
            </span>
          ))}
        </div>
        {truncated && (
          <div style={{ marginTop: 8, padding: "4px 8px", background: "#fef2f2", color: "#dc2626", borderRadius: 4, fontSize: 12 }}>
            ⚠️ 上下文已截断 — 部分消息被移除
          </div>
        )}
      </div>
    </ErrorBoundary>
  );
}
