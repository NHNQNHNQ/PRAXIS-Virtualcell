import type { ReactNode } from "react";

// 卡片壳(spec §3):暖白面板 + 细边框 + 16px 圆角 + 极浅阴影,层次靠间距/字重而非大色块。
// 可选 title 渲染为衬线小标题;可选 actions 渲染在标题行右侧(如下载/复制按钮位)。
// 纯展示原子,走 components.css 的 .card。

export type CardProps = {
  title?: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
};

export default function Card({ title, actions, children }: CardProps) {
  return (
    <section className="card">
      {(title != null || actions != null) && (
        <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: "var(--space-3)" }}>
          {title != null ? <h2>{title}</h2> : <span />}
          {actions != null && <div style={{ display: "flex", gap: "var(--space-2)" }}>{actions}</div>}
        </div>
      )}
      {children}
    </section>
  );
}
