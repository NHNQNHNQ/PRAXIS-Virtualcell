import type { ReactNode } from "react";

// 空态占位(加载完成但无数据时)。文案守 spec §3.5:中性、克制、无 AI/工程腔,
// 默认给可复用的"暂无内容";具体页面按需传入更贴切的 title(如"未产生模块路由")。
// hint 为可选的补充说明。纯展示原子,无副作用。

export type EmptyStateProps = {
  title?: ReactNode;
  hint?: ReactNode;
};

export default function EmptyState({ title = "暂无内容", hint }: EmptyStateProps) {
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
