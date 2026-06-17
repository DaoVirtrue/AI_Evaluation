import React, { useMemo, useCallback, useRef, useEffect } from "react";
import type { TrajectoryStep } from "@agent-viz/transform";
import { ErrorBoundary, EmptyState, sanitize } from "./shared";

export interface TrajectoryTimelineProps {
  steps: TrajectoryStep[];
  height?: number;
  width?: number | string;
  onStepClick?: (step: TrajectoryStep, index: number) => void;
  renderMode?: "auto" | "dom" | "canvas";
}

const STEP_COLORS: Record<string, string> = {
  llm_call: "#3b82f6",
  tool_call: "#22c55e",
  thinking: "#eab308",
  output: "#6366f1",
  error: "#ef4444",
};

export function TrajectoryTimeline({
  steps,
  height = 600,
  width = "100%",
  onStepClick,
  renderMode = "auto",
}: TrajectoryTimelineProps) {
  const useCanvas = renderMode === "canvas" || (renderMode === "auto" && steps.length > 1000);

  if (steps.length === 0) {
    return <EmptyState icon="📊" title="暂无轨迹数据" action="执行 Agent 后将在此显示推理步骤" />;
  }

  return (
    <ErrorBoundary>
      <div
        style={{
          height,
          width,
          overflowY: "auto",
          border: "1px solid #e5e7eb",
          borderRadius: 8,
          background: "#fff",
        }}
        role="list"
        aria-label="Agent trajectory timeline"
      >
        {useCanvas ? (
          <CanvasTimeline steps={steps.slice(0, 10000)} height={height} onStepClick={onStepClick} />
        ) : (
          steps.map((step, i) => (
            <div
              key={i}
              role="listitem"
              onClick={() => onStepClick?.(step, i)}
              style={{
                display: "flex",
                alignItems: "center",
                padding: "8px 16px",
                borderBottom: "1px solid #f3f4f6",
                cursor: "pointer",
                transition: "background 0.15s",
              }}
              onMouseEnter={(e) => (e.currentTarget.style.background = "#f9fafb")}
              onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
            >
              <span
                style={{
                  display: "inline-block",
                  width: 10,
                  height: 10,
                  borderRadius: "50%",
                  background: STEP_COLORS[step.type] || "#9ca3af",
                  marginRight: 12,
                  flexShrink: 0,
                }}
              />
              <span style={{ fontSize: 13, color: "#6b7280", minWidth: 32 }}>#{i + 1}</span>
              <span style={{ fontSize: 13, fontWeight: 500 }}>{formatStepType(step.type)}</span>
              {step.model && <span style={{ fontSize: 12, color: "#9ca3af", marginLeft: 8 }}>{step.model}</span>}
              {step.latencyMs != null && (
                <span style={{ fontSize: 12, color: "#9ca3af", marginLeft: "auto" }}>{step.latencyMs}ms</span>
              )}
            </div>
          ))
        )}
      </div>
    </ErrorBoundary>
  );
}

function CanvasTimeline({
  steps,
  height,
  onStepClick,
}: {
  steps: TrajectoryStep[];
  height: number;
  onStepClick?: (step: TrajectoryStep, index: number) => void;
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const dpr = window.devicePixelRatio || 1;
    canvas.width = canvas.offsetWidth * dpr;
    canvas.height = height * dpr;
    canvas.style.width = `${canvas.offsetWidth}px`;
    canvas.style.height = `${height}px`;
    const ctx = canvas.getContext("2d")!;
    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    const rowH = 28;
    steps.forEach((step, i) => {
      const y = i * rowH;
      if (y > height) return;
      ctx.fillStyle = STEP_COLORS[step.type] || "#9ca3af";
      ctx.fillRect(8, y + 8, 10, 10);
      ctx.fillStyle = "#374151";
      ctx.font = "12px sans-serif";
      ctx.fillText(`#${i + 1} ${formatStepType(step.type)}`, 26, y + 18);
    });
  }, [steps, height]);

  return <canvas ref={canvasRef} style={{ width: "100%", height }} />;
}

function formatStepType(type: string): string {
  const map: Record<string, string> = {
    llm_call: "LLM 调用",
    tool_call: "工具调用",
    thinking: "思考",
    output: "输出",
    error: "错误",
  };
  return map[type] || type;
}
