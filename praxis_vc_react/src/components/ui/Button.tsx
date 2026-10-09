import type { ButtonHTMLAttributes, ReactNode } from "react";


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
