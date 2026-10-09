import type { ReactNode } from "react";
import StatusPill, { type FieldStatus } from "./StatusPill";


export type FieldRowProps = {
  label: ReactNode;
  status?: FieldStatus;
  children: ReactNode;
};

export default function FieldRow({ label, status, children }: FieldRowProps) {
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "minmax(120px, 200px) 1fr",
        gap: "var(--space-3)",
        alignItems: "start",
        padding: "var(--space-2) 0",
        borderBottom: "1px solid var(--border)",
      }}
    >
      <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-1)" }}>
        <span style={{ fontSize: 13, color: "var(--text-muted)" }}>{label}</span>
        {status != null && <StatusPill status={status} />}
      </div>
      <div>{children}</div>
    </div>
  );
}
