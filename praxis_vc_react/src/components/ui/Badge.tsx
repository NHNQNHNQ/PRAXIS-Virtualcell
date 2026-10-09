import type { ReactNode } from "react";


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
