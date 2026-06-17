import React, { useEffect, useState, useRef } from "react";

const API = "http://localhost:8000/api/v1";
const inputStyle: React.CSSProperties = { width: "100%", padding: "8px 12px", border: "1px solid #d1d5db", borderRadius: 6, fontSize: 14, boxSizing: "border-box" as any };

export default function Datasets() {
  const [datasets, setDatasets] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploadName, setUploadName] = useState("");
  const [uploading, setUploading] = useState(false);
  const [preview, setPreview] = useState<any>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const fetchDatasets = () => {
    fetch(`${API}/datasets`).then(r => r.json()).then(setDatasets).catch(() => {}).finally(() => setLoading(false));
  };
  useEffect(() => { fetchDatasets(); }, []);

  const upload = async () => {
    const file = fileRef.current?.files?.[0];
    if (!file || !uploadName) return;
    setUploading(true);
    const form = new FormData();
    form.append("name", uploadName);
    form.append("file", file);
    try {
      await fetch(`${API}/datasets`, { method: "POST", body: form });
      setUploadName("");
      if (fileRef.current) fileRef.current.value = "";
      fetchDatasets();
    } catch (e: any) { alert("上传失败: " + e.message); }
    finally { setUploading(false); }
  };

  const previewDataset = async (id: string) => {
    const r = await fetch(`${API}/datasets/${id}/preview`);
    setPreview(await r.json());
  };

  const deleteDataset = async (id: string) => {
    await fetch(`${API}/datasets/${id}`, { method: "DELETE" });
    fetchDatasets();
  };

  if (loading) return <div style={{ textAlign: "center", padding: 48 }}>⏳ 加载中...</div>;

  return (
    <div style={{ maxWidth: 900 }}>
      <h1 style={{ fontSize: 24, fontWeight: 700, marginBottom: 24 }}>📁 数据集管理</h1>

      {/* Upload */}
      <div style={{ background: "#fff", borderRadius: 8, padding: 24, marginBottom: 24, boxShadow: "0 1px 3px rgba(0,0,0,0.1)" }}>
        <h3 style={{ fontSize: 15, fontWeight: 600, marginBottom: 12 }}>上传数据集</h3>
        <div style={{ display: "flex", gap: 12, alignItems: "flex-end" }}>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 13, fontWeight: 500, marginBottom: 4 }}>数据集名称</div>
            <input value={uploadName} onChange={e => setUploadName(e.target.value)} placeholder="例如: 基础问答测试集" style={inputStyle} />
          </div>
          <div style={{ flex: 2 }}>
            <div style={{ fontSize: 13, fontWeight: 500, marginBottom: 4 }}>JSONL 文件</div>
            <input ref={fileRef} type="file" accept=".jsonl,.json,.csv" style={inputStyle} />
          </div>
          <button onClick={upload} disabled={uploading || !uploadName} style={{
            padding: "8px 20px", background: uploading ? "#93c5fd" : "#3b82f6", color: "#fff",
            border: "none", borderRadius: 6, cursor: uploading ? "not-allowed" : "pointer", fontSize: 14, whiteSpace: "nowrap",
          }}>
            {uploading ? "上传中..." : "📤 上传"}
          </button>
        </div>
      </div>

      {/* Dataset List */}
      {datasets.length === 0 ? (
        <div style={{ textAlign: "center", padding: 48, background: "#fff", borderRadius: 8, color: "#9ca3af" }}>
          暂无数据集，请上传
        </div>
      ) : (
        <div style={{ background: "#fff", borderRadius: 8, boxShadow: "0 1px 3px rgba(0,0,0,0.1)", overflow: "hidden" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <thead>
              <tr style={{ background: "#f9fafb", borderBottom: "2px solid #e5e7eb", textAlign: "left" }}>
                <th style={th}>名称</th><th style={th}>格式</th><th style={th}>Case 数</th><th style={th}>上传时间</th><th style={th}>操作</th>
              </tr>
            </thead>
            <tbody>
              {datasets.map(d => (
                <tr key={d.id} style={{ borderBottom: "1px solid #f3f4f6" }}>
                  <td style={td}><strong>{d.name}</strong></td>
                  <td style={td}>{d.format}</td>
                  <td style={td}>{d.case_count}</td>
                  <td style={{ ...td, color: "#9ca3af" }}>{d.created_at?.slice(0, 16) || "—"}</td>
                  <td style={td}>
                    <button onClick={() => previewDataset(d.id)} style={actionBtn}>👁 预览</button>
                    <button onClick={() => deleteDataset(d.id)} style={{ ...actionBtn, color: "#ef4444" }}>🗑 删除</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Preview Modal */}
      {preview && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 100 }} onClick={() => setPreview(null)}>
          <div style={{ background: "#fff", borderRadius: 12, padding: 24, maxWidth: 600, width: "90%", maxHeight: "80vh", overflow: "auto" }} onClick={e => e.stopPropagation()}>
            <h3 style={{ marginBottom: 12 }}>📋 {preview.name} ({preview.case_count} cases)</h3>
            {preview.preview?.map((c: any, i: number) => (
              <div key={i} style={{ marginBottom: 8, padding: 8, background: "#f9fafb", borderRadius: 6, fontSize: 12 }}>
                <div><strong>{c.case_id}</strong></div>
                <div style={{ color: "#6b7280" }}>Q: {c.input}</div>
                <div style={{ color: "#166534" }}>A: {c.expected_output}</div>
              </div>
            ))}
            <button onClick={() => setPreview(null)} style={{ marginTop: 12, padding: "8px 20px", background: "#6b7280", color: "#fff", border: "none", borderRadius: 6, cursor: "pointer" }}>关闭</button>
          </div>
        </div>
      )}
    </div>
  );
}

const th: React.CSSProperties = { padding: "12px 16px", fontWeight: 600, color: "#374151", fontSize: 12 };
const td: React.CSSProperties = { padding: "12px 16px", color: "#374151" };
const actionBtn: React.CSSProperties = { border: "none", background: "none", color: "#3b82f6", cursor: "pointer", fontSize: 12, marginRight: 8 };
