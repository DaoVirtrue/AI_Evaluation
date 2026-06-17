import React, { useMemo } from "react";
import type { TrajectoryStep } from "@agent-viz/transform";
import { ErrorBoundary, EmptyState } from "./shared";

export interface AgentDiffViewProps {
  left: TrajectoryStep[];
  right: TrajectoryStep[];
  leftLabel?: string;
  rightLabel?: string;
}

export function AgentDiffView({ left, right, leftLabel = "A", rightLabel = "B" }: AgentDiffViewProps) {
  const diffs = useMemo(() => compareTrajectories(left, right), [left, right]);

  if (left.length === 0 && right.length === 0) return <EmptyState icon="🔍" title="无可对比数据" />;

  return (
    <ErrorBoundary>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, padding: 16 }}>
        <div style={{ fontWeight: 600, fontSize: 14, padding: 8, borderBottom: "2px solid #3b82f6" }}>{leftLabel} ({left.length} 步)</div>
        <div style={{ fontWeight: 600, fontSize: 14, padding: 8, borderBottom: "2px solid #22c55e" }}>{rightLabel} ({right.length} 步)</div>
        {diffs.slice(0, 200).map((diff, i) => (
          <React.Fragment key={i}>
            <div style={{ padding: "4px 8px", background: diff.different ? "#fef2f2" : "transparent", fontSize: 12, borderRadius: 4 }}>
              {diff.left ? `#${diff.left.index + 1} ${diff.left.type}` : "—"}
            </div>
            <div style={{ padding: "4px 8px", background: diff.different ? "#f0fdf4" : "transparent", fontSize: 12, borderRadius: 4 }}>
              {diff.right ? `#${diff.right.index + 1} ${diff.right.type}` : "—"}
            </div>
          </React.Fragment>
        ))}
        {diffs.length === 0 && <div style={{ gridColumn: "1 / -1", textAlign: "center", color: "#6b7280", padding: 16 }}>两个版本完全一致</div>}
      </div>
    </ErrorBoundary>
  );
}

function compareTrajectories(left: TrajectoryStep[], right: TrajectoryStep[]) {
  const max = Math.max(left.length, right.length);
  const diffs: { left?: TrajectoryStep; right?: TrajectoryStep; different: boolean }[] = [];
  for (let i = 0; i < max; i++) {
    const l = left[i];
    const r = right[i];
    diffs.push({
      left: l,
      right: r,
      different: l?.type !== r?.type || l?.toolName !== r?.toolName,
    });
  }
  return diffs;
}
