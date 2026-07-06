import type { ButtonHTMLAttributes, ReactNode } from "react";

// 无状态按钮原子。variant 走 components.css 的 .btn / .btn-ghost / .btn-danger;
// size="sm" 叠加 .btn-sm。深靛蓝实心为主(spec §3,不用黑),ghost 描边,danger 用于破坏性操作。
// 纯展示,无副作用、无数据请求;供后续 Stage/tab 复用。

export type ButtonVariant = "primary" | "ghost" | "danger";
export type ButtonSize = "sm" | "md";

export type ButtonProps = {
  variant?: ButtonVariant;
  size?: ButtonSize;
  children: ReactNode;
} & Omit<ButtonHTMLAttributes<HTMLButtonElement>, "className">;

const VARIANT_CLASS: Record<ButtonVariant, string> = {
  primary: "btn",
  ghost: "btn btn-ghost",
  danger: "btn btn-danger",
};

export default function Button({
  variant = "primary",
  size = "md",
  type = "button",
  children,
  ...rest
}: ButtonProps) {
  const className = size === "sm" ? `${VARIANT_CLASS[variant]} btn-sm` : VARIANT_CLASS[variant];
  return (
    <button type={type} className={className} {...rest}>
      {children}
    </button>
  );
}
