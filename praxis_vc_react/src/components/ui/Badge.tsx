import type { ReactNode } from "react";

// 状态徽标(spec §2 字段/状态语义)。tone 决定配色,全部走 components.css 的 .badge* 类:
//   confirmed → 主色   inferred/warn → 警告色   missing/danger → 危险色   neutral → 中性描边
// 纯展示原子,无副作用。

export type BadgeTone =
  | "confirmed"
  | "inferred"
  | "missing"
  | "neutral"
  | "warn"
  | "danger";

export type BadgeProps = {
  tone: BadgeTone;
  children: ReactNode;
};

// tone → .badge 修饰类。warn 复用 inferred,danger 复用 missing,neutral 用基类。
const TONE_CLASS: Record<BadgeTone, string> = {
  confirmed: "badge badge-confirmed",
  inferred: "badge badge-inferred",
  missing: "badge badge-missing",
  neutral: "badge",
  warn: "badge badge-inferred",
  danger: "badge badge-missing",
};

export default function Badge({ tone, children }: BadgeProps) {
  return <span className={TONE_CLASS[tone]}>{children}</span>;
}
