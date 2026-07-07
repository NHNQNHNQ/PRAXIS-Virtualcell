import type { CSSProperties } from "react";
import type { ModulePlan, ModulePlanEntry } from "../../api";
import Card from "../ui/Card";
import Badge from "../ui/Badge";
import EmptyState from "../ui/EmptyState";
import Skeleton from "../ui/Skeleton";
import { ModuleRoutingGraph } from "../visualization";

// Stage 5 · Module Routing tab(spec §2 Module Routing / §3.5 / 红线 3)——展示本次运行**实际**产生的
// 模块路由结果(run 后 /module-plan 返回的 ModulePlan)。与 Stage 3 Route 的静态预期(cell preset
// 声明的「预计涉及的功能模块」)明确区分:此处是运行产物,不是运行前的预期。
//
// 主体:P4 手写 SVG ModuleRoutingGraph(primary/secondary/handoff/verdict/abstain)
//     + primary/secondary/overall_verdict 摘要 + entries 降级表(module/role/verdict/mismatch,
//       迁自旧 views/ResultView 的 ModuleRoutingBlock)。
// 降级:plan 为 null(加载中/未到)→ Skeleton;plan 为 {}/不可路由 → EmptyState(迁现有语义)。
//
// 铁律(红线 3):只渲染 plan 的真实字段,不重算真实路由、不编造 verdict/reliability;配色走 token。

// plan 是否"实质为空"(null / {} / 无 primary 且 entries 空 且 secondary 空)。
// 与 ModuleRoutingGraph.isEmptyPlan 判定对齐,保证图与表降级一致。
function isEmptyPlan(
  plan: ModulePlan | Record<string, never> | null,
): plan is null | Record<string, never> {
  if (plan == null) return true;
  const p = plan as Partial<ModulePlan>;
  const noPrimary = p.primary == null || p.primary === "";
  const noEntries = !Array.isArray(p.entries) || p.entries.length === 0;
  const noSecondary = !Array.isArray(p.secondary) || p.secondary.length === 0;
  return noPrimary && noEntries && noSecondary;
}

// verdict → Badge 语义色(与 ModuleRoutingGraph 的 verdictStyle 语义一致)。
// ok/accept → confirmed / caution → warn / mismatch → danger / abstain / 其余 → neutral。
function verdictTone(verdict: string): "confirmed" | "warn" | "danger" | "neutral" {
  const v = verdict.toLowerCase();
  if (v === "ok" || v === "accept" || v === "accepted") return "confirmed";
  if (v === "caution") return "warn";
  if (v === "mismatch") return "danger";
  return "neutral";
}

// ── 小样式(走 token,不硬编码配色)──
const codeStyle: CSSProperties = {
  fontFamily: "var(--font-mono)",
  fontSize: 12,
  background: "var(--code-bg)",
  border: "1px solid var(--border)",
  borderRadius: "var(--radius-sm)",
  padding: "1px 6px",
  color: "var(--text)",
  wordBreak: "break-word",
};
const rowStyle: CSSProperties = {
  display: "flex",
  gap: "var(--space-3)",
  alignItems: "baseline",
  flexWrap: "wrap",
  fontSize: 13,
  color: "var(--text-muted)",
};
const labelStyle: CSSProperties = { minWidth: 96, color: "var(--text-muted)" };
const stackStyle: CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "var(--space-4)",
};

function Mono({ children }: { children: string }) {
  return <code style={codeStyle}>{children}</code>;
}

// entries 降级表(module/role/verdict/mismatch)。迁自旧 ResultView.ModuleRoutingBlock,
// 复用 App.css 的 .table-scroll / .kv-table / .module-table 结构类;verdict 加 Badge 语义色。
function EntriesTable({ entries }: { entries: ModulePlanEntry[] }) {
  if (entries.length === 0) {
    return (
      <p style={{ color: "var(--text-muted)", fontSize: 13, margin: 0 }}>无模块条目。</p>
    );
  }
  return (
    <div className="table-scroll">
      <table className="kv-table module-table">
        <thead>
          <tr>
            <th>模块</th>
            <th>角色</th>
            <th>判定</th>
            <th>不匹配</th>
          </tr>
        </thead>
        <tbody>
          {entries.map((e, i) => {
            const verdict = e.verdict || "";
            return (
              <tr key={e.module ?? i}>
                <td>
                  <code style={codeStyle}>{e.module || "—"}</code>
                </td>
                <td>{e.role || "—"}</td>
                <td>
                  {verdict ? (
                    <Badge tone={verdictTone(verdict)}>{verdict}</Badge>
                  ) : (
                    "—"
                  )}
                </td>
                <td>{e.mismatch ?? "—"}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export default function ModuleRoutingTab({
  plan,
}: {
  plan: ModulePlan | Record<string, never> | null;
}) {
  // 加载中/未到:Skeleton。
  if (plan === null) {
    return <Skeleton lines={6} />;
  }

  // 顶部标注:红线 3 —— 明确这是 run 后的实际路由,与 Stage 3 的静态预期区分。
  const header = (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: "var(--space-1)",
        padding: "var(--space-3) var(--space-4)",
        borderRadius: "var(--radius)",
        border: "1px solid var(--border)",
        background: "color-mix(in srgb, var(--primary) 6%, var(--surface))",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
        <Badge tone="confirmed">实际路由(run 产物)</Badge>
        <strong style={{ fontSize: 14, color: "var(--text)" }}>本次运行实际的模块路由</strong>
      </div>
      <span style={{ fontSize: 13, color: "var(--text-muted)" }}>
        与提问阶段的「预计涉及的功能模块」不同,这里是本次运行实际的模块路由与判定。
      </span>
    </div>
  );

  // 不可路由(空 {} / abstain):EmptyState 降级,保留头部标注。
  if (isEmptyPlan(plan)) {
    return (
      <div style={stackStyle}>
        {header}
        <EmptyState
          title="未产生模块路由"
          hint="本次运行未产生可展示的主/辅模块路由(不可路由或已弃权)。"
        />
      </div>
    );
  }

  const full = plan as ModulePlan;
  const secondary = Array.isArray(full.secondary) ? full.secondary : [];
  const entries = Array.isArray(full.entries) ? full.entries : [];

  return (
    <div style={stackStyle}>
      {header}

      {/* 主体图:P4 手写 SVG 模块关系图(primary 居中,secondary 环绕,verdict 着色)。 */}
      <Card title="模块路由关系">
        <ModuleRoutingGraph plan={full} />
      </Card>

      {/* 摘要:primary / secondary / overall_verdict(只读真实字段)。 */}
      <Card title="路由摘要">
        <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-2)" }}>
          <div style={rowStyle}>
            <span style={labelStyle}>主模块</span>
            <span style={{ color: "var(--text)", flex: 1 }}>
              <Mono>{full.primary || "—"}</Mono>
            </span>
          </div>
          <div style={rowStyle}>
            <span style={labelStyle}>辅模块</span>
            <span style={{ color: "var(--text)", flex: 1 }}>
              <Mono>{secondary.length ? secondary.join(", ") : "—"}</Mono>
            </span>
          </div>
          <div style={rowStyle}>
            <span style={labelStyle}>总体判定</span>
            <span style={{ color: "var(--text)", flex: 1 }}>
              {full.overall_verdict ? (
                <Badge tone={verdictTone(full.overall_verdict)}>{full.overall_verdict}</Badge>
              ) : (
                "—"
              )}
            </span>
          </div>
        </div>
      </Card>

      {/* entries 降级表:module / role / verdict / mismatch。 */}
      <Card title="模块明细">
        <EntriesTable entries={entries} />
      </Card>
    </div>
  );
}
