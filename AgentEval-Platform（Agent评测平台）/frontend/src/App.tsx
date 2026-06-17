import React from "react";
import { BrowserRouter, Routes, Route, Link } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import Dashboard from "./pages/Dashboard";
import EvaluationDetail from "./pages/EvaluationDetail";
import CreateEvaluation from "./pages/CreateEvaluation";
import Datasets from "./pages/Datasets";

const queryClient = new QueryClient({ defaultOptions: { queries: { retry: 1, staleTime: 30_000 } } });

const navLink: React.CSSProperties = { color: "#d1d5db", textDecoration: "none", fontSize: 14 };

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <div style={{ minHeight: "100vh", background: "#f3f4f6" }}>
          <nav style={{ background: "#1f2937", color: "#fff", padding: "12px 24px", display: "flex", gap: 24, alignItems: "center" }}>
            <Link to="/" style={{ color: "#fff", fontWeight: 700, fontSize: 18, textDecoration: "none" }}>🤖 AgentEval Platform</Link>
            <Link to="/" style={navLink}>📊 评测列表</Link>
            <Link to="/create" style={navLink}>➕ 创建评测</Link>
            <Link to="/datasets" style={navLink}>📁 数据集</Link>
          </nav>
          <main style={{ maxWidth: 1200, margin: "0 auto", padding: 24 }}>
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/evaluations/:id" element={<EvaluationDetail />} />
              <Route path="/create" element={<CreateEvaluation />} />
              <Route path="/datasets" element={<Datasets />} />
            </Routes>
          </main>
        </div>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
