import type { CSSProperties } from "react";


export type FieldStatus = "confirmed" | "inferred" | "missing" | "editable" | "locked";

const DOT_CLASS: Record<FieldStatus, string> = {
  confirmed: "status-dot confirmed",
  inferred: "status-dot inferred",
  missing: "status-dot missing",
  editable: "status-dot",
  locked: "status-dot",
};

const LABEL: Record<FieldStatus, string> = {
  confirmed: "Confirmed",
  inferred: "Inferred",
  missing: "Missing",
  editable: "Editable",
  locked: "Locked",
};

const NEUTRAL_DOT: CSSProperties = { border: "1px solid var(--border)" };

export type StatusPillProps = {
  status: FieldStatus;
};

export default function StatusPill({ status }: StatusPillProps) {
  const neutral = status === "editable" || status === "locked";
  return (
    <span className="pill">
      <span className={DOT_CLASS[status]} style={neutral ? NEUTRAL_DOT : undefined} />
      {LABEL[status]}
    </span>
  );
}
