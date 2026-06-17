import React, { useState, useEffect, useRef } from "react";
import type { TrajectoryStep } from "@agent-viz/transform";
import { ErrorBoundary, EmptyState } from "./shared";

export interface ThinkingStreamPlayerProps {
  steps: TrajectoryStep[];
}

export function ThinkingStreamPlayer({ steps }: ThinkingStreamPlayerProps) {
  const thinking = steps.filter((s) => s.type === "thinking" || s.type === "llm_call");
  if (thinking.length === 0) return <EmptyState icon="💭" title="无思考过程数据" />;

  const [stepIdx, setStepIdx] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(1);
  const timer = useRef<ReturnType<typeof setInterval>>();

  useEffect(() => {
    if (playing) {
      timer.current = setInterval(() => {
        setStepIdx((i) => {
          if (i >= thinking.length - 1) {
            setPlaying(false);
            return i;
          }
          return i + 1;
        });
      }, 500 / speed);
      return () => clearInterval(timer.current);
    }
  }, [playing, speed, thinking.length]);

  const step = thinking[stepIdx];
  const text = step?.llmOutput || `Step ${stepIdx + 1}`;

  return (
    <ErrorBoundary>
      <div style={{ padding: 16 }}>
        <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
          <button onClick={() => setPlaying(!playing)} style={btnStyle}>
            {playing ? "⏸ 暂停" : "▶ 播放"}
          </button>
          <select value={speed} onChange={(e) => setSpeed(Number(e.target.value))} style={selectStyle}>
            <option value={0.5}>0.5×</option>
            <option value={1}>1×</option>
            <option value={2}>2×</option>
            <option value={4}>4×</option>
            <option value={8}>8×</option>
          </select>
          <span style={{ fontSize: 12, color: "#6b7280", alignSelf: "center" }}>
            {stepIdx + 1} / {thinking.length}
          </span>
          <input
            type="range"
            min={0}
            max={thinking.length - 1}
            value={stepIdx}
            onChange={(e) => setStepIdx(Number(e.target.value))}
            style={{ flex: 1 }}
          />
        </div>
        <div style={{ background: "#f9fafb", border: "1px solid #e5e7eb", borderRadius: 8, padding: 16, minHeight: 200, fontFamily: "monospace", fontSize: 13, whiteSpace: "pre-wrap", maxHeight: 400, overflowY: "auto" }}>
          {text}
        </div>
      </div>
    </ErrorBoundary>
  );
}

const btnStyle: React.CSSProperties = {
  padding: "6px 16px",
  border: "1px solid #d1d5db",
  borderRadius: 6,
  background: "#fff",
  cursor: "pointer",
  fontSize: 13,
};

const selectStyle: React.CSSProperties = {
  padding: "4px 8px",
  border: "1px solid #d1d5db",
  borderRadius: 6,
  fontSize: 13,
};
