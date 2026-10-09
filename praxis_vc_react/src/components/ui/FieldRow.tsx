import type { ReactNode } from "react";
import StatusPill, { type FieldStatus } from "./StatusPill";

// Review 表单行(spec §2):左侧标签 + 可选状态点,右侧值或输入控件(children)。
// status 复用 StatusPill 的字段状态集;省略则不显状态点。
// 纯展示原子(布局壳),无副作用;实际输入控件由调用方作为 children 传入。

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
