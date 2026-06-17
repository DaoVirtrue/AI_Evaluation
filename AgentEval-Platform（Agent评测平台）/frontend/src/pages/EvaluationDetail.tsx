import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";

const API = "http://localhost:8000/api/v1";

type Result = { id: string; case_id: string; input: string; expected_output: string; actual_output: string; passed: boolean; score: number; token_usage: any; latency_ms: number };
type Stats = { total: number; passed: number; failed: number; pass_rate: number; total_tokens: number; total_cost: number; avg_latency_ms: number };

export default function EvaluationDetail() {
  const { id } = useParams<{ id: string }>();
  const [evalData, setEvalData] = useState<any>(null);
  const [stats, setStats] = useState<Stats | null>(null);
  const [results, setResults] = useState<Result[]>([]);
  const [filter, setFilter] = useState("all");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    Promise.all([
      fetch(`${API}/evaluations/${id}`).then(r => r.json()),
      fetch(`${API}/evaluations/${id}/stats`).then(r => r.json()),
      fetch(`${API}/evaluations/${id}/results?filter=${filter}`).then(r => r.json()),
    ]).then(([ev, st, rs]) => {
      setEvalData(ev); setStats(st); setResults((rs as any).items || []);
    }).catch(() => {}).finally(() => setLoading(false));
  }, [id, filter]);

  if (loading) return <div style={{ textAlign: "center", padding: 48 }}>⏳ 加载中...</div>;
  if (!evalData) return <div style={{ textAlign: "center", padding: 48, color: "#ef4444" }}>评测不存在</div>;

  const statusMap: Record<string, { color: string; bg: string; text: string }> = {
    queued: { color: "#6b7280", bg: "#f3f4f6", text: "排队中" },
    running: { color: "#1e40af", bg: "#dbeafe", text: "运行中" },
    completed: { color: "#166534", bg: "#dcfce7", text: "已完成" },
    failed: { color: "#dc2626", bg: "#fef2f2", text: "失败" },
    cancelled: { color: "#92400e", bg: "#fef3c7", text: "已取消" },
  };
  const st = statusMap[evalData.status] || statusMap.queued;

  return (
    <div>
      <Link to="/" style={{ color: "#3b82f6", fontSize: 13 }}>← 返回列表</Link>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", margin: "12px 0" }}>
        <h1 style={{ fontSize: 24, fontWeight: 700 }}>{evalData.name}</h1>
        <span style={{ padding: "4px 14px", borderRadius: 16, fontSize: 13, fontWeight: 600, background: st.bg, color: st.color }}>{st.text}</span>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(6, 1fr)", gap: 12, marginBottom: 24 }}>
          {[
            { label: "通过率", value: `${stats.pass_rate}%`, color: stats.pass_rate >= 80 ? "#166534" : stats.pass_rate >= 50 ? "#92400e" : "#dc2626" },
            { label: "通过", value: stats.passed, color: "#166534" },
            { label: "失败", value: stats.failed, color: "#dc2626" },
            { label: "平均延迟", value: `${stats.avg_latency_ms}ms`, color: "#1e40af" },
            { label: "Token消耗", value: stats.total_tokens.toLocaleString(), color: "#6b7280" },
            { label: "成本", value: `$${stats.total_cost.toFixed(6)}`, color: "#6b7280" },
          ].map((s, i) => (
            <div key={i} style={{ background: "#fff", borderRadius: 8, padding: 16, textAlign: "center", boxShadow: "0 1px 3px rgba(0,0,0,0.1)" }}>
              <div style={{ fontSize: 12, color: "#6b7280", marginBottom: 4 }}>{s.label}</div>
              <div style={{ fontSize: 22, fontWeight: 700, color: s.color }}>{s.value}</div>
            </div>
          ))}
        </div>
      )}

      {/* Filter Tabs */}
      <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
        {["all", "passed", "failed"].map(f => (
          <button key={f} onClick={() => setFilter(f)} style={{
            padding: "6px 16px", borderRadius: 6, border: "1px solid #d1d5db",
            background: filter === f ? "#3b82f6" : "#fff", color: filter === f ? "#fff" : "#374151",
            cursor: "pointer", fontSize: 13,
          }}>
            {f === "all" ? "全部" : f === "passed" ? "✅ 通过" : "❌ 失败"}
          </button>
        ))}
        <span style={{ fontSize: 13, color: "#6b7280", alignSelf: "center" }}>共 {stats?.total || 0} 条</span>
      </div>

      {/* Results Table */}
      {results.length === 0 ? (
        <div style={{ textAlign: "center", padding: 48, background: "#fff", borderRadius: 8, color: "#9ca3af" }}>
          暂无结果数据（评测可能还在排队中或未生成结果）
        </div>
      ) : (
        <div style={{ background: "#fff", borderRadius: 8, boxShadow: "0 1px 3px rgba(0,0,0,0.1)", overflow: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
            <thead>
              <tr style={{ background: "#f9fafb", borderBottom: "2px solid #e5e7eb", textAlign: "left" }}>
                <th style={th}>#</th><th style={th}>Case ID</th><th style={th}>输入</th><th style={th}>期望</th><th style={th}>实际</th><th style={th}>结果</th><th style={th}>Token</th><th style={th}>延迟</th>
              </tr>
            </thead>
            <tbody>
              {results.map((r, i) => (
                <tr key={r.id} style={{ borderBottom: "1px solid #f3f4f6" }}>
                  <td style={td}>{i + 1}</td>
                  <td style={td}>{r.case_id}</td>
                  <td style={{ ...td, maxWidth: 180, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={r.input}>{r.input?.slice(0, 60) || "—"}</td>
                  <td style={td}>{r.expected_output?.slice(0, 40) || "—"}</td>
                  <td style={{ ...td, maxWidth: 180, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={r.actual_output}>{r.actual_output?.slice(0, 60) || "—"}</td>
                  <td style={td}>{r.passed ? <span style={{ color: "#166534" }}>✅</span> : <span style={{ color: "#dc2626" }}>❌</span>}</td>
                  <td style={td}>{((r.token_usage || {}).prompt_tokens || 0) + ((r.token_usage || {}).completion_tokens || 0)}</td>
                  <td style={td}>{r.latency_ms ? `${r.latency_ms}ms` : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

const th: React.CSSProperties = { padding: "10px 12px", fontWeight: 600, color: "#374151", fontSize: 11, textTransform: "uppercase" };
const td: React.CSSProperties = { padding: "10px 12px", color: "#374151" };
