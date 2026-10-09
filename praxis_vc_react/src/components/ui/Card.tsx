import type { ReactNode } from "react";

// 卡片壳(spec §3):中性面板 + 细边框 + 16px 圆角 + 极浅阴影,层次靠间距/字重而非大色块。
// 可选 title 渲染为无衬线小标题;可选 actions 渲染在标题行右侧(如下载/复制按钮位)。
// 纯展示原子,走 components.css 的 .card。

export type CardProps = {
  title?: ReactNode;
  actions?: ReactNode;
  ariaLabel?: string;
  actionsLabel?: string;
  children: ReactNode;
};

export default function Card({
  title,
  actions,
  ariaLabel,
  actionsLabel,
  children,
}: CardProps) {
  return (
    <section className="card" aria-label={ariaLabel}>
      {(title != null || actions != null) && (
        <div className="card-header">
          {title != null ? <h2>{title}</h2> : <span />}
          {actions != null && (
            <div
              className="card-actions"
              role={actionsLabel ? "group" : undefined}
              aria-label={actionsLabel}
            >
              {actions}
            </div>
          )}
        </div>
      )}
      {children}
    </section>
  );
}
