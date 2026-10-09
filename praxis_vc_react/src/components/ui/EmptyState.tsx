import type { ReactNode } from "react";


export type EmptyStateProps = {
  title?: ReactNode;
  hint?: ReactNode;
};

export default function EmptyState({ title = "No content yet", hint }: EmptyStateProps) {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        gap: "var(--space-2)",
        padding: "var(--space-6) var(--space-4)",
        textAlign: "center",
        color: "var(--text-muted)",
      }}
    >
      <div style={{ fontSize: 14, fontWeight: 500, color: "var(--text)" }}>{title}</div>
      {hint != null && <div style={{ fontSize: 13 }}>{hint}</div>}
    </div>
  );
}
