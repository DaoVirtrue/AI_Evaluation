import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";

const API = "http://localhost:8000/api/v1";
type Eval = { id: string; name: string; status: string; total_cases: number; completed_cases: number; created_at: string; metrics?: any; agent_config?: any };

const statusStyle: Record<string, React.CSSProperties> = {
  queued: { background: "#f3f4f6", color: "#6b7280" },
  running: { background: "#dbeafe", color: "#1e40af" },
  completed: { background: "#dcfce7", color: "#166534" },
  failed: { background: "#fef2f2", color: "#dc2626" },
  cancelled: { background: "#fef3c7", color: "#92400e" },
};

export default function Dashboard() {
  const [evals, setEvals] = useState<Eval[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchEvals = () => {
    fetch(`${API}/evaluations?project_id=default`)
      .then(r => r.json()).then(d => setEvals(d.items || [])).catch(() => {})
      .finally(() => setLoading(false));
  };
  useEffect(() => { fetchEvals(); }, []);

  const cancelEval = async (id: string) => {
    await fetch(`${API}/evaluations/${id}`, { method: "DELETE" });
    fetchEvals();
  };

  const stats = {
    total: evals.length,
    completed: evals.filter(e => e.status === "completed").length,
    running: evals.filter(e => e.status === "running").length,
    passRate: evals.filter(e => e.metrics?.pass_rate).length > 0
      ? Math.round(evals.filter(e => e.metrics?.pass_rate).reduce((s, e) => s + (e.metrics?.pass_rate || 0), 0) / evals.filter(e => e.metrics?.pass_rate).length)
      : null,
  };

  if (loading) return <div style={{ textAlign: "center", padding: 48, color: "#6b7280" }}>⏳ 加载中...</div>;

  return (
    <div>
      {/* Stats Cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16, marginBottom: 24 }}>
        {[
          { label: "评测总数", value: stats.total, icon: "📊" },
          { label: "运行中", value: stats.running, icon: "🔄" },
          { label: "已完成", value: stats.completed, icon: "✅" },
          { label: "平均通过率", value: stats.passRate !== null ? `${stats.passRate}%` : "—", icon: "📈" },
        ].map((s, i) => (
          <div key={i} style={{ background: "#fff", borderRadius: 8, padding: 20, boxShadow: "0 1px 3px rgba(0,0,0,0.1)" }}>
            <div style={{ fontSize: 24, marginBottom: 4 }}>{s.icon}</div>
            <div style={{ fontSize: 13, color: "#6b7280" }}>{s.label}</div>
            <div style={{ fontSize: 28, fontWeight: 700, color: "#111827" }}>{s.value}</div>
          </div>
        ))}
      </div>

      {/* Evaluations Table */}
      {evals.length === 0 ? (
        <div style={{ textAlign: "center", padding: 64, background: "#fff", borderRadius: 8, boxShadow: "0 1px 3px rgba(0,0,0,0.1)" }}>
          <p style={{ fontSize: 48, marginBottom: 8 }}>📊</p>
          <p style={{ fontSize: 16, color: "#6b7280", marginBottom: 16 }}>暂无评测任务</p>
          <Link to="/create" style={{ padding: "10px 24px", background: "#3b82f6", color: "#fff", borderRadius: 6, textDecoration: "none", fontSize: 14 }}>
            创建第一个评测
          </Link>
        </div>
      ) : (
        <div style={{ background: "#fff", borderRadius: 8, boxShadow: "0 1px 3px rgba(0,0,0,0.1)", overflow: "hidden" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <thead>
              <tr style={{ background: "#f9fafb", borderBottom: "2px solid #e5e7eb", textAlign: "left" }}>
                <th style={th}>名称</th>
                <th style={th}>模型</th>
                <th style={th}>状态</th>
                <th style={th}>通过率</th>
                <th style={th}>进度</th>
                <th style={th}>创建时间</th>
                <th style={th}>操作</th>
              </tr>
            </thead>
            <tbody>
              {evals.map(e => {
                const model = (e.agent_config || {}).model || "—";
                const passRate = e.metrics?.pass_rate !== undefined ? `${e.metrics.pass_rate}%` : "—";
                return (
                  <tr key={e.id} style={{ borderBottom: "1px solid #f3f4f6" }}>
                    <td style={td}>
                      <Link to={`/evaluations/${e.id}`} style={{ color: "#3b82f6", textDecoration: "none", fontWeight: 500 }}>
                        {e.name}
                      </Link>
                    </td>
                    <td style={td}>{model}</td>
                    <td style={td}>
                      <span style={{ ...statusStyle[e.status] || {}, padding: "2px 10px", borderRadius: 12, fontSize: 12 }}>{e.status}</span>
                    </td>
                    <td style={td}>{passRate}</td>
                    <td style={td}>{e.completed_cases}/{e.total_cases}</td>
                    <td style={{ ...td, color: "#9ca3af" }}>{e.created_at?.slice(0, 16) || "—"}</td>
                    <td style={td}>
                      {e.status === "running" || e.status === "queued" ? (
                        <button onClick={() => cancelEval(e.id)} style={{ border: "none", background: "none", color: "#ef4444", cursor: "pointer", fontSize: 12 }}>取消</button>
                      ) : null}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

const th: React.CSSProperties = { padding: "12px 16px", fontWeight: 600, color: "#374151", fontSize: 12, textTransform: "uppercase" };
const td: React.CSSProperties = { padding: "12px 16px", color: "#374151" };
