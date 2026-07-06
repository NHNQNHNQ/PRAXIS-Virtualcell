import { type Mode } from "../../api";

export type Theme = "light" | "dark";

// TopBar(Task 9.6)—— 主工作区顶栏(spec §1)。
// 含:mode pill(offline ⇄ llm_assisted 切换)、LLM 提示 pill、light/dark 主题开关。
// 主题实际切换(document.documentElement.dataset.theme)由 AppShell 管,这里只发起 onToggleTheme。
// 前端只读展示,不参与预测/治理决策。
//
// 【文案 · spec §3.5】LLM 提示不照抄旧「⚠ LLM 未参与预测/治理决策」(工程黑话),
// 按 §3.5 改写对照表用自然科学家说法。mode 切换按钮同理避免工程旁白。

const LLM_NOTICE = "结果由确定性模型给出,未经语言模型改写";

const MODE_LABEL: Record<Mode, string> = {
  offline: "本地模式",
  llm_assisted: "语言模型辅助",
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
      {/* mode pill:当前模式 + 一键切到另一模式(不改预测口径,仅前端展示模式) */}
      <span className="tb-mode">
        <span className="tb-mode-label">{MODE_LABEL[mode]}</span>
        <button
          type="button"
          className="tb-mode-toggle"
          onClick={() => onMode(nextMode)}
          title={`切换到「${MODE_LABEL[nextMode]}」`}
        >
          切换
        </button>
      </span>

      {/* LLM 提示 pill —— 自然说法(spec §3.5) */}
      <span className="tb-notice">
        <span className="tb-notice-dot" />
        {LLM_NOTICE}
      </span>

      {/* 主题开关(light/dark) */}
      <button
        type="button"
        className="tb-theme"
        onClick={onToggleTheme}
        title={isDark ? "切换到浅色" : "切换到深色"}
        aria-label={isDark ? "切换到浅色主题" : "切换到深色主题"}
      >
        <span className="tb-theme-icon">{isDark ? "☀" : "☾"}</span>
        {isDark ? "浅色" : "深色"}
      </button>
    </div>
  );
}
