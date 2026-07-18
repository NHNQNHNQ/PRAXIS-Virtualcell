import { type Stage } from "../../api";

// StepperRail(Task 9.7)—— 主工作区内部左侧的 5 阶段竖向进度轨(spec §1)。
// 注意:这是「工作区内」的阶段轨,不是全局侧栏(全局历史 job 侧栏是 JobSidebar)。
//
// 规则(spec §6 stepper):
//  - 当前阶段:高亮(--primary);
//  - 已完成阶段(在当前之前):可点回退(回退只改 stage 不清 JobState 字段,故不丢数据);
//  - 未满足 canEnter 的靠后阶段:禁用置灰,点不动;
//  - 不允许跳过 review:即便更靠后的阶段恰好可达,也不能从 ask 直接跳到 route 之后
//    ——本组件只允许点「当前之前(回退)」或「紧邻的下一个且 canEnter」的阶段,天然不跳步。
// 文案守 spec §3.5:阶段名用平实中文(提问/核对/路由/运行/结果),不用工程黑话。

// 5 阶段的固定顺序与平实中文名(与 api.ts 的 Stage 一一对应)。
const STAGES: { key: Stage; label: string; hint: string }[] = [
  { key: "ask", label: "提问", hint: "描述要预测的扰动实验" },
  { key: "review", label: "核对", hint: "核对并确认解析出的请求" },
  { key: "route", label: "路由", hint: "查看模块与物种适配" },
  { key: "run", label: "运行", hint: "确认参数并执行预测" },
  { key: "results", label: "结果", hint: "查看预测报告与溯源" },
];

// 单个阶段的可视状态:done=已完成(可回退)、current=当前、enabled=可前进、disabled=不可达。
type NodeState = "done" | "current" | "enabled" | "disabled";

export default function StepperRail({
  stage,
  canEnter,
  onJump,
}: {
  stage: Stage;
  canEnter: (s: Stage) => boolean;
  onJump: (s: Stage) => void;
}) {
  const currentIdx = STAGES.findIndex((s) => s.key === stage);

  // 计算某阶段相对当前阶段的可视/可点状态。
  //  - 靠前(idx<current):已完成,可点回退;
  //  - 当前(idx===current):高亮,不重复触发跳转;
  //  - 紧邻下一个(idx===current+1)且 canEnter:可前进点击(逐步推进,不跳过 review);
  //  - 其余靠后阶段:一律禁用(既未达标,也不允许跨步跳过中间阶段)。
  function nodeState(idx: number): NodeState {
    if (idx < currentIdx) return "done";
    if (idx === currentIdx) return "current";
    if (idx === currentIdx + 1 && canEnter(STAGES[idx].key)) return "enabled";
    return "disabled";
  }

  return (
    <nav className="sr-rail" aria-label="阶段进度">
      <ol className="sr-list">
        {STAGES.map((s, idx) => {
          const state = nodeState(idx);
          const clickable = state === "done" || state === "enabled";
          const isLast = idx === STAGES.length - 1;
          // 当前阶段不 disable(保留 aria-current 语义),仅点击无动作;
          // 只有真正未达标/不可跳过的阶段(disabled)才禁用。
          return (
            <li key={s.key} className="sr-item">
              <button
                type="button"
                className={`sr-node sr-${state}`}
                disabled={state === "disabled"}
                aria-current={state === "current" ? "step" : undefined}
                title={s.hint}
                onClick={() => {
                  if (clickable) onJump(s.key);
                }}
              >
                <span className="sr-marker" aria-hidden="true">
                  {state === "done" ? "✓" : idx + 1}
                </span>
                <span className="sr-text">
                  <span className="sr-label">{s.label}</span>
                  <span className="sr-hint">{s.hint}</span>
                </span>
              </button>
              {!isLast && (
                <span
                  className={`sr-connector ${idx < currentIdx ? "sr-connector-done" : ""}`}
                  aria-hidden="true"
                />
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
