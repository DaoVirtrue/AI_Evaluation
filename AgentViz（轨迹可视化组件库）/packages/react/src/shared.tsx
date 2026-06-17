import React, { ReactNode } from "react";

/** Error boundary: catches render errors, shows fallback instead of white screen */
export class ErrorBoundary extends React.Component<
  { children: ReactNode; fallback?: ReactNode },
  { hasError: boolean; error: Error | null }
> {
  state = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error("[AgentViz] Component error:", error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        this.props.fallback || (
          <div style={{ padding: 16, color: "#999", textAlign: "center" }}>
            <p>Component render error</p>
            <p style={{ fontSize: 12 }}>{this.state.error?.message}</p>
          </div>
        )
      );
    }
    return this.props.children;
  }
}

/** Empty state placeholder */
export function EmptyState({ icon, title, action }: { icon?: string; title: string; action?: string }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", padding: 48, color: "#999" }}>
      {icon && <div style={{ fontSize: 48, marginBottom: 16 }}>{icon}</div>}
      <p style={{ fontSize: 16, margin: 0 }}>{title}</p>
      {action && <p style={{ fontSize: 14, color: "#666" }}>{action}</p>}
    </div>
  );
}

/** Sanitize user text before rendering */
export function sanitize(text: string): string {
  if (typeof DOMPurify !== "undefined") {
    return (window as any).DOMPurify.sanitize(text);
  }
  return text.replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

import DOMPurify from "dompurify";
