import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

const API = "http://localhost:8000/api/v1";
const MODELS = [
  "claude-fable-5","claude-opus-4-8","claude-sonnet-4-6","claude-haiku-4-5",
  "gpt-5.5","gpt-5.4","gpt-4.1","gpt-4.1-mini","gpt-4.1-nano",
  "deepseek-v4-pro","deepseek-v4-flash",
  "gemini-3.1-pro","gemini-3.5-flash","gemini-3.1-flash-lite",
];

const btn: React.CSSProperties = { padding: "10px 24px", border: "none", borderRadius: 6, cursor: "pointer", fontSize: 14, fontWeight: 500 };
const inputStyle: React.CSSProperties = { width: "100%", padding: "8px 12px", border: "1px solid #d1d5db", borderRadius: 6, fontSize: 14, boxSizing: "border-box" as any };

export default function CreateEvaluation() {
  const [name, setName] = useState("");
  const [model, setModel] = useState("claude-sonnet-4-6");
  const [maxCases, setMaxCases] = useState(10);
  const [framework, setFramework] = useState("native");
  const [scoring, setScoring] = useState("contains");
  const [systemPrompt, setSystemPrompt] = useState("You are a helpful assistant.");
  const [selectedDataset, setSelectedDataset] = useState("");
  const [datasets, setDatasets] = useState<any[]>([]);
  const [preview, setPreview] = useState<any[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    fetch(`${API}/datasets`).then(r => r.json()).then(setDatasets).catch(() => {});
  }, []);

  const selectDataset = async (did: string) => {
    setSelectedDataset(did);
    if (!did) { setPreview([]); return; }
    const r = await fetch(`${API}/datasets/${did}/preview`);
    const d = await r.json();
    setPreview(d.preview || []);
  };

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name) return;
    setSubmitting(true);
    try {
      const r = await fetch(`${API}/evaluations`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name,
          agent_config: { model, framework, system_prompt: systemPrompt, scoring_method: scoring, dataset_id: selectedDataset },
          max_cases: maxCases,
        }),
      });
      if (!r.ok) throw new Error(await r.text());
      const data = await r.json();
      navigate(`/evaluations/${data.id}`);
    } catch (err: any) {
      alert("创建失败: " + err.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div style={{ maxWidth: 700 }}>
      <h1 style={{ fontSize: 24, fontWeight: 700, marginBottom: 24 }}>➕ 创建评测</h1>
      <form onSubmit={submit} style={{ background: "#fff", borderRadius: 8, padding: 24, boxShadow: "0 1px 3px rgba(0,0,0,0.1)" }}>
        {/* Basic */}
        <Section title="基本信息">
          <Label>评测名称 *</Label>
          <input value={name} onChange={e => setName(e.target.value)} required placeholder="例如: Sonnet vs Opus 对比测试" style={inputStyle} />
        </Section>

        {/* Dataset */}
        <Section title="📁 数据集">
          <Label>选择数据集</Label>
          <select value={selectedDataset} onChange={e => selectDataset(e.target.value)} style={inputStyle}>
            <option value="">— 不选择数据集 —</option>
            {datasets.map(d => <option key={d.id} value={d.id}>{d.name} ({d.case_count} cases)</option>)}
          </select>
          {preview.length > 0 && (
            <div style={{ marginTop: 8, background: "#f9fafb", borderRadius: 6, padding: 12, fontSize: 12, maxHeight: 200, overflow: "auto" }}>
              <div style={{ fontWeight: 600, marginBottom: 8 }}>数据预览 (前 {preview.length} 条):</div>
              {preview.map((c, i) => (
                <div key={i} style={{ marginBottom: 6, paddingBottom: 6, borderBottom: "1px solid #e5e7eb" }}>
                  <span style={{ color: "#6b7280" }}>{c.case_id}:</span> {c.input?.slice(0, 80)}{c.input?.length > 80 ? "..." : ""}
                </div>
              ))}
            </div>
          )}
          <div style={{ marginTop: 8 }}>
            <a href="/datasets" style={{ color: "#3b82f6", fontSize: 13 }}>📤 上传新数据集</a>
          </div>
        </Section>

        {/* Agent Config */}
        <Section title="🤖 Agent 配置">
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            <div>
              <Label>框架</Label>
              <select value={framework} onChange={e => setFramework(e.target.value)} style={inputStyle}>
                <option value="native">Native (AgentForge)</option>
                <option value="langchain">LangChain</option>
                <option value="openai_agents">OpenAI Agents SDK</option>
              </select>
            </div>
            <div>
              <Label>模型</Label>
              <select value={model} onChange={e => setModel(e.target.value)} style={inputStyle}>
                {MODELS.map(m => <option key={m} value={m}>{m}</option>)}
              </select>
            </div>
          </div>
          <div style={{ marginTop: 12 }}>
            <Label>System Prompt</Label>
            <textarea value={systemPrompt} onChange={e => setSystemPrompt(e.target.value)} rows={3} style={{ ...inputStyle, resize: "vertical" }} />
          </div>
          <div style={{ marginTop: 12, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            <div>
              <Label>评分方式</Label>
              <select value={scoring} onChange={e => setScoring(e.target.value)} style={inputStyle}>
                <option value="contains">包含匹配</option>
                <option value="exact">精确匹配</option>
              </select>
            </div>
            <div>
              <Label>最大 Case 数</Label>
              <input type="number" value={maxCases} onChange={e => setMaxCases(Number(e.target.value))} min={1} max={1000} style={inputStyle} />
            </div>
          </div>
        </Section>

        <button type="submit" disabled={submitting || !name} style={{
          ...btn, background: submitting || !name ? "#93c5fd" : "#3b82f6", color: "#fff", marginTop: 16,
          cursor: submitting || !name ? "not-allowed" : "pointer",
        }}>
          {submitting ? "⏳ 创建中..." : "🚀 创建评测"}
        </button>
      </form>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: 20, paddingBottom: 20, borderBottom: "1px solid #f3f4f6" }}>
      <h3 style={{ fontSize: 15, fontWeight: 600, marginBottom: 12, color: "#374151" }}>{title}</h3>
      {children}
    </div>
  );
}
function Label({ children }: { children: string }) {
  return <div style={{ marginBottom: 4, fontSize: 13, fontWeight: 500, color: "#374151" }}>{children}</div>;
}
