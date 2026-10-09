import { useMemo, useState } from "react";
import type { TraceStep } from "../../api";
import EmptyState from "../ui/EmptyState";
type TraceNode = {
  index: number;
  messageId: string | null;
  sender: string | null;
  receiver: string | null;
  messageType: string | null;
  timestamp: string | null;
};

export type AgentTraceTimelineProps = {
  trace: TraceStep[];
};

const CONDENSED_TARGET = 8;

function readStr(step: TraceStep, key: string): string | null {
  const v = step[key];
  return typeof v === "string" && v !== "" ? v : null;
}

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

function condense(nodes: TraceNode[]): TraceNode[] {
  const n = nodes.length;
  if (n <= CONDENSED_TARGET) return nodes;

  const keep = new Set<number>();
  keep.add(0);
  keep.add(n - 1);
  for (let i = 1; i < n; i++) {
    if (nodes[i].messageType !== nodes[i - 1].messageType) {
      keep.add(i);
    }
  }

  let chosen = [...keep].sort((a, b) => a - b);

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

const VIEW_W = 640;
const ROW_H = 64;
const PAD_TOP = 24;
const PAD_BOTTOM = 24;
const AXIS_X = 120;
const DOT_R = 7;

const MISSING = "—";

function display(value: string | null): string {
  return value != null ? value : MISSING;
}

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

      <circle
        cx={AXIS_X}
        cy={y}
        r={DOT_R}
        fill={isFirst || isLast ? "var(--primary)" : "var(--surface)"}
        stroke={isFirst || isLast ? "var(--primary)" : "var(--accent)"}
        strokeWidth={2}
      />

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
  const [expandedAll, setExpandedAll] = useState(false);
  const [openIndex, setOpenIndex] = useState<number | null>(null);

  const nodes = useMemo(
    () => (Array.isArray(trace) ? toNodes(trace) : []),
    [trace],
  );
  const condensed = useMemo(() => condense(nodes), [nodes]);

  if (nodes.length === 0) {
    return (
      <EmptyState title="No execution trace available" hint="This result contains no step-by-step execution trace." />
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
          Execution trace · {nodes.length} steps
          {!expandedAll && canExpand ? `, condensed to ${condensed.length} steps` : ""}
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
            {expandedAll ? "Collapse" : `Show all steps(${nodes.length})`}
          </button>
        )}
      </div>

      <div style={{ width: "100%", overflowX: "auto" }}>
        <svg
          viewBox={`0 0 ${VIEW_W} ${viewH}`}
          width="100%"
          preserveAspectRatio="xMidYMin meet"
          role="list"
          aria-label={`Execution timeline, ${nodes.length} steps`}
          style={{ display: "block", minWidth: 320, maxWidth: "100%" }}
        >
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
          <DetailRow label="Step" value={`#${openNode.index + 1}`} />
          <DetailRow label="message_id" value={display(openNode.messageId)} />
          <DetailRow label="timestamp" value={display(openNode.timestamp)} />
          <DetailRow label="sender" value={display(openNode.sender)} />
          <DetailRow label="receiver" value={display(openNode.receiver)} />
          <DetailRow label="message_type" value={display(openNode.messageType)} />
        </div>
      )}

      {!expandedAll && canExpand && (
        <div
          style={{
            fontFamily: "var(--font-sans)",
            fontSize: 12,
            color: "var(--text-muted)",
          }}
        >
          The condensed view shows the first and last steps and stage changes. Select a node for its fields, or expand all steps.
        </div>
      )}
    </div>
  );
}

function DetailRow({ label, value }: { label: string; value: string }) {
  return (
    <>
      <span style={{ color: "var(--text-muted)" }}>{label}</span>
      <span style={{ color: "var(--text)", wordBreak: "break-all" }}>{value}</span>
    </>
  );
}
