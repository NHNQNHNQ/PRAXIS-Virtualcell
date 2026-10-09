import type { ReactNode } from "react";


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
