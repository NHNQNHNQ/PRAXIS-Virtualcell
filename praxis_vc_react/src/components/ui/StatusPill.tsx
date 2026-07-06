import type { CSSProperties } from "react";

// 字段状态点 + 标签(spec §2:confirmed/inferred/missing/editable/locked)。
// confirmed=深靛蓝勾选态、inferred=amber(推断)、missing=红橙(缺失);
// editable=可编辑(中性,铅笔意味)、locked=不可改(中性,锁意味)。
// 走 components.css 的 .pill + .status-dot 类;editable/locked 无状态色,用中性描边。
// 纯展示原子,无副作用。

export type FieldStatus = "confirmed" | "inferred" | "missing" | "editable" | "locked";

// status → 状态点修饰类(缺省的 editable/locked 不着色,仅描边 pill)。
const DOT_CLASS: Record<FieldStatus, string> = {
  confirmed: "status-dot confirmed",
  inferred: "status-dot inferred",
  missing: "status-dot missing",
  editable: "status-dot",
  locked: "status-dot",
};

// status → 中文标签(严谨、无 AI/工程腔)。
const LABEL: Record<FieldStatus, string> = {
  confirmed: "已确认",
  inferred: "推断",
  missing: "缺失",
  editable: "可编辑",
  locked: "锁定",
};

// editable/locked 的状态点无语义色,借边框描出以免透明不可见。
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
