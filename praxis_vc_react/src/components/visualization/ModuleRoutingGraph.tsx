import type { ModulePlan, ModulePlanEntry } from "../../api";
import EmptyState from "../ui/EmptyState";

// 模块路由网络图(spec §4 ④ / §2 Route:module routing graph)。
// 纯展示、无状态、无副作用、不请求数据:数据由 P5 的 ModuleRoutingTab 从 /module-plan
// 取到 ModulePlan(或空对象)后传入。
// spec §4 明确"模块网络图 → 手写 SVG"且"暂不做花哨 force graph",故此处不引任何图库,
// 布局用确定性算法:primary 居中大节点,secondary 均匀环形排布(角度 = i/n*2π),
// primary→secondary 用连线(handoff)。坐标完全由节点数推导,不用随机。
//
// 节点着色按 verdict(取自 entries 中对应 module 的 verdict):
//   ok/accept → --accent(翠绿) / caution → --warn(amber) / mismatch → --danger(red)。
//   abstain → 虚线边框特殊标记(中性描边,不着 verdict 色)。
//   未知/缺失 verdict → 中性(--text-muted 描边),不假造裁决。
// confidence:ModulePlan 无该字段,故不以节点大小/标签编造置信度。
// 文案守 spec §3.5:节点标签用模块 display_name(缺则 module code),不外泄内部实现旁白。

export type ModuleRoutingGraphProps = {
  plan: ModulePlan | Record<string, never> | null;
};

// —— 画布几何(viewBox 单位;通过 viewBox 响应式缩放,不写死像素)——
const VIEW_W = 640;
const VIEW_H = 440;
const CX = VIEW_W / 2;
const CY = VIEW_H / 2;
const RING_R = 150; // secondary 环半径
const PRIMARY_R = 44; // primary 节点半径
const SECONDARY_R = 34; // secondary 节点半径

// verdict → 描边/填充色(走 token 变量,不硬编码 hex)。
// 返回 stroke(边框)与 fill(浅底,用半透明经由 opacity 呈现)。
type NodeStyle = { stroke: string; label: string };

function verdictStyle(verdict: string | undefined): NodeStyle {
  const v = (verdict ?? "").toLowerCase();
  if (v === "ok" || v === "accept" || v === "accepted") {
    return { stroke: "var(--accent)", label: "通过" };
  }
  if (v === "caution") {
    return { stroke: "var(--warn)", label: "留意" };
  }
  if (v === "mismatch") {
    return { stroke: "var(--danger)", label: "不匹配" };
  }
  if (v === "abstain") {
    return { stroke: "var(--text-muted)", label: "弃权" };
  }
  // 未知/缺失:中性描边,不假造裁决。
  return { stroke: "var(--text-muted)", label: v === "" ? "" : verdict ?? "" };
}

function isAbstain(verdict: string | undefined): boolean {
  return (verdict ?? "").toLowerCase() === "abstain";
}

// 从 entries 里按 module code 建索引,方便按节点取 verdict/display_name。
function indexEntries(entries: ModulePlanEntry[]): Map<string, ModulePlanEntry> {
  const map = new Map<string, ModulePlanEntry>();
  for (const e of entries) {
    if (e.module) map.set(e.module, e);
  }
  return map;
}

// 取节点展示名:优先 entry.display_name,退回 module code。
function nodeLabel(code: string, entry: ModulePlanEntry | undefined): string {
  const name = entry?.display_name;
  return name != null && name !== "" ? name : code;
}

// 判定 plan 是否"实质为空"(null / {} / 无 primary 且 entries 空)。
function isEmptyPlan(plan: ModuleRoutingGraphProps["plan"]): plan is null | Record<string, never> {
  if (plan == null) return true;
  const p = plan as Partial<ModulePlan>;
  const noPrimary = p.primary == null || p.primary === "";
  const noEntries = !Array.isArray(p.entries) || p.entries.length === 0;
  const noSecondary = !Array.isArray(p.secondary) || p.secondary.length === 0;
  return noPrimary && noEntries && noSecondary;
}

// 单个节点(圆 + 标签 + 可选状态注记)。abstain 用虚线边框。
function GraphNode({
  x,
  y,
  r,
  label,
  style,
  abstain,
  isPrimary,
}: {
  x: number;
  y: number;
  r: number;
  label: string;
  style: NodeStyle;
  abstain: boolean;
  isPrimary: boolean;
}) {
  return (
    <g>
      <circle
        cx={x}
        cy={y}
        r={r}
        fill={isPrimary ? "var(--primary)" : "var(--surface)"}
        stroke={isPrimary ? "var(--primary)" : style.stroke}
        strokeWidth={isPrimary ? 2 : 2.5}
        strokeDasharray={abstain ? "5 4" : undefined}
      />
      <text
        x={x}
        y={y + 4}
        textAnchor="middle"
        style={{
          fontFamily: "var(--font-sans)",
          fontSize: isPrimary ? 14 : 12,
          fontWeight: isPrimary ? 600 : 500,
          fill: isPrimary ? "var(--surface)" : "var(--text)",
        }}
      >
        {label.length > 12 ? `${label.slice(0, 11)}…` : label}
      </text>
      {/* 状态注记置于节点下方(primary 无 verdict 注记)。 */}
      {!isPrimary && style.label !== "" && (
        <text
          x={x}
          y={y + r + 14}
          textAnchor="middle"
          style={{
            fontFamily: "var(--font-sans)",
            fontSize: 11,
            fill: style.stroke,
          }}
        >
          {style.label}
        </text>
      )}
    </g>
  );
}

export default function ModuleRoutingGraph({ plan }: ModuleRoutingGraphProps) {
  if (isEmptyPlan(plan)) {
    return <EmptyState title="未产生模块路由" hint="此次结果未包含主/辅模块的路由信息。" />;
  }

  // 到此 plan 必为完整 ModulePlan(isEmptyPlan 已排除空形态)。
  const full = plan as ModulePlan;
  const primary = full.primary;
  const secondary = Array.isArray(full.secondary) ? full.secondary : [];
  const entries = Array.isArray(full.entries) ? full.entries : [];
  const entryMap = indexEntries(entries);

  const primaryEntry = primary ? entryMap.get(primary) : undefined;
  const primaryLabel = primary ? nodeLabel(primary, primaryEntry) : "主模块";

  // secondary 均匀环形排布:角度从正上方(-90°)起,顺时针分布。
  const n = secondary.length;
  const nodes = secondary.map((code, i) => {
    const angle = (i / Math.max(n, 1)) * 2 * Math.PI - Math.PI / 2;
    const x = CX + RING_R * Math.cos(angle);
    const y = CY + RING_R * Math.sin(angle);
    const entry = entryMap.get(code);
    const verdict = entry?.verdict;
    return {
      code,
      x,
      y,
      label: nodeLabel(code, entry),
      style: verdictStyle(verdict),
      abstain: isAbstain(verdict),
    };
  });

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-3)" }}>
      {/* overflow-x:auto 防窄屏横向溢出;SVG 通过 viewBox 响应式缩放。 */}
      <div style={{ width: "100%", overflowX: "auto" }}>
        <svg
          viewBox={`0 0 ${VIEW_W} ${VIEW_H}`}
          width="100%"
          preserveAspectRatio="xMidYMid meet"
          role="img"
          aria-label="模块路由关系图:主模块居中,辅模块环绕"
          style={{ display: "block", minWidth: 320, maxWidth: "100%" }}
        >
          {/* ① handoff 连线:primary → 每个 secondary(先画,压在节点下)。 */}
          {nodes.map((node) => (
            <line
              key={`edge-${node.code}`}
              x1={CX}
              y1={CY}
              x2={node.x}
              y2={node.y}
              stroke="var(--border)"
              strokeWidth={1.5}
            />
          ))}

          {/* ② secondary 环节点。 */}
          {nodes.map((node) => (
            <GraphNode
              key={`node-${node.code}`}
              x={node.x}
              y={node.y}
              r={SECONDARY_R}
              label={node.label}
              style={node.style}
              abstain={node.abstain}
              isPrimary={false}
            />
          ))}

          {/* ③ primary 中心大节点(最后画,压在最上)。 */}
          <GraphNode
            x={CX}
            y={CY}
            r={PRIMARY_R}
            label={primaryLabel}
            style={{ stroke: "var(--primary)", label: "" }}
            abstain={false}
            isPrimary
          />
        </svg>
      </div>

      {/* 图例:verdict 色说明(走 token,便于阅读)。 */}
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          gap: "var(--space-3)",
          fontFamily: "var(--font-sans)",
          fontSize: 12,
          color: "var(--text-muted)",
        }}
      >
        <LegendDot color="var(--primary)" text="主模块" filled />
        <LegendDot color="var(--accent)" text="通过" />
        <LegendDot color="var(--warn)" text="留意" />
        <LegendDot color="var(--danger)" text="不匹配" />
        <LegendDot color="var(--text-muted)" text="弃权(虚线)" dashed />
      </div>
    </div>
  );
}

// 图例小圆点。filled 为主模块实心示意;dashed 表示弃权虚线边框。
function LegendDot({
  color,
  text,
  filled,
  dashed,
}: {
  color: string;
  text: string;
  filled?: boolean;
  dashed?: boolean;
}) {
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: "var(--space-1)" }}>
      <svg width={14} height={14} aria-hidden="true">
        <circle
          cx={7}
          cy={7}
          r={5}
          fill={filled ? color : "var(--surface)"}
          stroke={color}
          strokeWidth={1.5}
          strokeDasharray={dashed ? "3 2" : undefined}
        />
      </svg>
      {text}
    </span>
  );
}
