import { useMemo, useState } from "react";
import type { TraceStep } from "../../api";
import EmptyState from "../ui/EmptyState";

// 运行轨迹时间线(spec §4 ⑤ / §2 Trace)。
// 纯展示、不请求数据:trace 由 P5 的 TraceTab(9.22)从 /trace 取到后传入。
// spec §4 明确"Trace → 手写 SVG + HTML timeline"且本期不引任何图库,故此处全手写。
//
// 真实 trace 步字段(见 runs/*/trace.json,api.ts 的 TraceStep = Record<string, unknown>):
//   { message_id, sender, receiver, message_type, timestamp } —— 全为字符串。
//   timestamp 为单调序号 token(如 "t0001"),非真实时钟,故按数组顺序 + timestamp 词序展示。
// 字段值可空/缺失(TraceStep 是宽类型),一律经窄化取值,缺失显占位不崩。
//
// 默认精简:确定性取"首、尾、message_type 变化点(阶段边界)"共 6–8 个节点;
// 变化点过多时再按等距抽样收敛到 ~8,始终保留首尾与顺序。提供"展开完整步骤"显全部。
// 精简纯确定性(边界 + 等距),不用 Math.random。
//
// 文案守 spec §3.5:trace 属 Stage 5 审计区,sender/receiver/message_type 等精确术语可展示,
// 但整体呈现克制,加必要中文引导(运行轨迹 / 展开完整步骤 / 折叠)。

// —— 窄化后的时间线节点(从 TraceStep 提取的稳定视图)——
type TraceNode = {
  index: number; // 原始数组下标(稳定标识 + 顺序)
  messageId: string | null;
  sender: string | null;
  receiver: string | null;
  messageType: string | null;
  timestamp: string | null;
};

export type AgentTraceTimelineProps = {
  trace: TraceStep[];
};

// 目标精简节点数上限(spec:默认 6–8 个)。
const CONDENSED_TARGET = 8;

// 从宽类型 TraceStep 里安全取一个字符串字段(非字符串/缺失→null)。
function readStr(step: TraceStep, key: string): string | null {
  const v = step[key];
  return typeof v === "string" && v !== "" ? v : null;
}

// 将原始 trace 窄化为节点数组,保持原始顺序。
function toNodes(trace: TraceStep[]): TraceNode[] {
  return trace.map((step, index) => ({
    index,
    messageId: readStr(step, "message_id"),
    sender: readStr(step, "sender"),
    receiver: readStr(step, "receiver"),
    messageType: readStr(step, "message_type"),
    timestamp: readStr(step, "timestamp"),
  }));
}

// 确定性精简:保留首、尾、以及 message_type 相对上一步发生变化的"阶段边界"节点。
// 若边界节点仍多于目标数,则在保留首尾前提下按等距索引抽样收敛到 ~CONDENSED_TARGET。
// 全程不引入随机;输入相同则输出相同。
function condense(nodes: TraceNode[]): TraceNode[] {
  const n = nodes.length;
  if (n <= CONDENSED_TARGET) return nodes;

  // ① 边界集合:首、尾、message_type 变化点。用下标集合去重并保序。
  const keep = new Set<number>();
  keep.add(0);
  keep.add(n - 1);
  for (let i = 1; i < n; i++) {
    if (nodes[i].messageType !== nodes[i - 1].messageType) {
      keep.add(i);
    }
  }

  let chosen = [...keep].sort((a, b) => a - b);

  // ② 边界过多 → 在保留首尾前提下等距抽样到 ~CONDENSED_TARGET(确定性)。
  if (chosen.length > CONDENSED_TARGET) {
    const sampled = new Set<number>();
    sampled.add(chosen[0]);
    sampled.add(chosen[chosen.length - 1]);
    const step = (chosen.length - 1) / (CONDENSED_TARGET - 1);
    for (let k = 1; k < CONDENSED_TARGET - 1; k++) {
      sampled.add(chosen[Math.round(k * step)]);
    }
    chosen = [...sampled].sort((a, b) => a - b);
  }

  return chosen.map((i) => nodes[i]);
}

// —— 时间线几何(viewBox 单位;经 viewBox 响应式缩放,不写死像素)——
const VIEW_W = 640;
const ROW_H = 64; // 每个节点行高
const PAD_TOP = 24;
const PAD_BOTTOM = 24;
const AXIS_X = 120; // 竖直时间轴的 x 位置
const DOT_R = 7;

// 一个占位符(字段缺失时显示,克制不臆造)。
const MISSING = "—";

function display(value: string | null): string {
  return value != null ? value : MISSING;
}

// 单个时间线节点行:左侧时间轴上的圆点 + 右侧 sender→receiver / message_type 文本。
// hover 经 <title> 显完整字段(时间 / 类型 / 收发方);节点点击展开该步全部字段。
function TimelineRow({
  node,
  y,
  isFirst,
  isLast,
  expanded,
  onToggle,
}: {
  node: TraceNode;
  y: number;
  isFirst: boolean;
  isLast: boolean;
  expanded: boolean;
  onToggle: (index: number) => void;
}) {
  const tip =
    `#${node.index + 1}` +
    ` · ${display(node.messageType)}` +
    ` · ${display(node.sender)} → ${display(node.receiver)}` +
    ` · ${display(node.timestamp)}`;

  return (
    <g
      style={{ cursor: "pointer" }}
      onClick={() => onToggle(node.index)}
      role="listitem"
      aria-label={tip}
    >
      <title>{tip}</title>

      {/* 圆点:首尾用主色实心,中间步用强调色描边空心。 */}
      <circle
        cx={AXIS_X}
        cy={y}
        r={DOT_R}
        fill={isFirst || isLast ? "var(--primary)" : "var(--surface)"}
        stroke={isFirst || isLast ? "var(--primary)" : "var(--accent)"}
        strokeWidth={2}
      />

      {/* 序号(轴左侧)。 */}
      <text
        x={AXIS_X - 18}
        y={y + 4}
        textAnchor="end"
        style={{
          fontFamily: "var(--font-mono)",
          fontSize: 11,
          fill: "var(--text-muted)",
        }}
      >
        {display(node.timestamp)}
      </text>

      {/* 主行:sender → receiver。 */}
      <text
        x={AXIS_X + 20}
        y={y - 2}
        style={{
          fontFamily: "var(--font-sans)",
          fontSize: 13,
          fontWeight: 500,
          fill: "var(--text)",
        }}
      >
        {display(node.sender)} → {display(node.receiver)}
      </text>

      {/* 副行:message_type(审计区精确术语,用等宽字承载)。 */}
      <text
        x={AXIS_X + 20}
        y={y + 15}
        style={{
          fontFamily: "var(--font-mono)",
          fontSize: 12,
          fill: "var(--text-muted)",
        }}
      >
        {display(node.messageType)}
        {expanded && node.messageId != null ? `  ·  ${node.messageId}` : ""}
      </text>
    </g>
  );
}

export default function AgentTraceTimeline({ trace }: AgentTraceTimelineProps) {
  // 内部状态:是否展开完整步骤;以及被点开查看细节的单步下标集合。
  const [expandedAll, setExpandedAll] = useState(false);
  const [openIndex, setOpenIndex] = useState<number | null>(null);

  const nodes = useMemo(
    () => (Array.isArray(trace) ? toNodes(trace) : []),
    [trace],
  );
  const condensed = useMemo(() => condense(nodes), [nodes]);

  // 空 trace(undefined / 非数组 / 空数组)→ 空态降级,不崩。
  if (nodes.length === 0) {
    return (
      <EmptyState title="暂无运行轨迹" hint="此次结果未记录逐步的运行轨迹。" />
    );
  }

  const shown = expandedAll ? nodes : condensed;
  const hiddenCount = nodes.length - condensed.length;
  const canExpand = hiddenCount > 0;

  const viewH = PAD_TOP + PAD_BOTTOM + Math.max(shown.length - 1, 0) * ROW_H;

  const toggleOpen = (index: number) => {
    setOpenIndex((cur) => (cur === index ? null : index));
  };
  const openNode = openIndex != null ? nodes.find((x) => x.index === openIndex) ?? null : null;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-3)" }}>
      {/* 头部:标题 + 计数 + 展开/折叠按钮。 */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          flexWrap: "wrap",
          gap: "var(--space-2)",
        }}
      >
        <div
          style={{
            fontFamily: "var(--font-sans)",
            fontSize: 13,
            color: "var(--text-muted)",
          }}
        >
          运行轨迹 · 共 {nodes.length} 步
          {!expandedAll && canExpand ? `,精简显示 ${condensed.length} 步` : ""}
        </div>
        {canExpand && (
          <button
            type="button"
            onClick={() => setExpandedAll((v) => !v)}
            style={{
              fontFamily: "var(--font-sans)",
              fontSize: 13,
              color: "var(--primary)",
              background: "transparent",
              border: "1px solid var(--border)",
              borderRadius: "var(--radius-sm)",
              padding: "var(--space-1) var(--space-3)",
              cursor: "pointer",
            }}
          >
            {expandedAll ? "折叠" : `展开完整步骤(${nodes.length})`}
          </button>
        )}
      </div>

      {/* overflow-x:auto 防窄屏横向溢出;SVG 经 viewBox 响应式缩放。 */}
      <div style={{ width: "100%", overflowX: "auto" }}>
        <svg
          viewBox={`0 0 ${VIEW_W} ${viewH}`}
          width="100%"
          preserveAspectRatio="xMidYMin meet"
          role="list"
          aria-label={`运行轨迹时间线,共 ${nodes.length} 步`}
          style={{ display: "block", minWidth: 320, maxWidth: "100%" }}
        >
          {/* 竖直时间轴。 */}
          {shown.length > 1 && (
            <line
              x1={AXIS_X}
              y1={PAD_TOP}
              x2={AXIS_X}
              y2={PAD_TOP + (shown.length - 1) * ROW_H}
              stroke="var(--border)"
              strokeWidth={1.5}
            />
          )}

          {/* 各节点行。 */}
          {shown.map((node, i) => (
            <TimelineRow
              key={node.messageId ?? `idx-${node.index}`}
              node={node}
              y={PAD_TOP + i * ROW_H}
              isFirst={node.index === 0}
              isLast={node.index === nodes.length - 1}
              expanded={expandedAll}
              onToggle={toggleOpen}
            />
          ))}
        </svg>
      </div>

      {/* 点开某步的细节面板(HTML,精确字段;点同一步再收起)。 */}
      {openNode && (
        <div
          style={{
            border: "1px solid var(--border)",
            borderRadius: "var(--radius-sm)",
            padding: "var(--space-3)",
            background: "var(--surface)",
            fontFamily: "var(--font-mono)",
            fontSize: 12,
            color: "var(--text)",
            display: "grid",
            gridTemplateColumns: "auto 1fr",
            gap: "var(--space-1) var(--space-3)",
          }}
        >
          <DetailRow label="步骤" value={`#${openNode.index + 1}`} />
          <DetailRow label="message_id" value={display(openNode.messageId)} />
          <DetailRow label="timestamp" value={display(openNode.timestamp)} />
          <DetailRow label="sender" value={display(openNode.sender)} />
          <DetailRow label="receiver" value={display(openNode.receiver)} />
          <DetailRow label="message_type" value={display(openNode.messageType)} />
        </div>
      )}

      {/* 提示:精简规则(克制说明,便于审计者理解取样)。 */}
      {!expandedAll && canExpand && (
        <div
          style={{
            fontFamily: "var(--font-sans)",
            fontSize: 12,
            color: "var(--text-muted)",
          }}
        >
          默认按首尾与阶段变化点精简;点击节点查看该步字段,或展开完整步骤。
        </div>
      )}
    </div>
  );
}

// 细节面板里的一行 label/value(等宽,审计友好)。
function DetailRow({ label, value }: { label: string; value: string }) {
  return (
    <>
      <span style={{ color: "var(--text-muted)" }}>{label}</span>
      <span style={{ color: "var(--text)", wordBreak: "break-all" }}>{value}</span>
    </>
  );
}
