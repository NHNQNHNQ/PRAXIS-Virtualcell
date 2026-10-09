import { type Mode } from "../../api";

export type Theme = "light" | "dark";
const LLM_NOTICE =
  "Language models only parse and explain; they do not produce numerical predictions or final decisions";

const MODE_LABEL: Record<Mode, string> = {
  offline: "Local mode",
  llm_assisted: "Language assistance",
};

export default function TopBar({
  mode,
  onMode,
  theme,
  onToggleTheme,
}: {
  mode: Mode;
  onMode: (m: Mode) => void;
  theme: Theme;
  onToggleTheme: () => void;
}) {
  const nextMode: Mode = mode === "offline" ? "llm_assisted" : "offline";
  const isDark = theme === "dark";

  return (
    <div className="tb-bar">
      <span className="tb-mode">
        <span className="tb-mode-label">{MODE_LABEL[mode]}</span>
        <button
          type="button"
          className="tb-mode-toggle"
          onClick={() => onMode(nextMode)}
          title={`Switch to ${MODE_LABEL[nextMode]}`}
        >
          Switch
        </button>
      </span>

      <span className="tb-notice">
        <span className="tb-notice-dot" />
        {LLM_NOTICE}
      </span>

      <button
        type="button"
        className="tb-theme"
        onClick={onToggleTheme}
        title={isDark ? "Switch to light" : "Switch to dark"}
        aria-label={isDark ? "Switch to light theme" : "Switch to dark theme"}
      >
        <span className="tb-theme-icon">{isDark ? "☀" : "☾"}</span>
        {isDark ? "Light" : "Dark"}
      </button>
    </div>
  );
}
