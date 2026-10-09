import type { ModulePlan, ModulePlanEntry } from "../../api";
import EmptyState from "../ui/EmptyState";

export type ModuleRoutingGraphProps = {
  plan: ModulePlan | Record<string, never> | null;
};

const VIEW_W = 640;
const VIEW_H = 440;
const CX = VIEW_W / 2;
const CY = VIEW_H / 2;
const RING_R = 150;
const PRIMARY_R = 44;
const SECONDARY_R = 34;

type NodeStyle = { stroke: string; label: string };

function verdictStyle(verdict: string | undefined): NodeStyle {
  const v = (verdict ?? "").toLowerCase();
  if (v === "ok" || v === "accept" || v === "accepted") {
    return { stroke: "var(--accent)", label: "Passed" };
  }
  if (v === "caution") {
    return { stroke: "var(--warn)", label: "Caution" };
  }
  if (v === "mismatch") {
    return { stroke: "var(--danger)", label: "Mismatch" };
  }
  if (v === "abstain") {
    return { stroke: "var(--text-muted)", label: "Abstained" };
  }
  return { stroke: "var(--text-muted)", label: v === "" ? "" : verdict ?? "" };
}

function isAbstain(verdict: string | undefined): boolean {
  return (verdict ?? "").toLowerCase() === "abstain";
}

function indexEntries(entries: ModulePlanEntry[]): Map<string, ModulePlanEntry> {
  const map = new Map<string, ModulePlanEntry>();
  for (const e of entries) {
    if (e.module) map.set(e.module, e);
  }
  return map;
}

function nodeLabel(code: string, entry: ModulePlanEntry | undefined): string {
  const name = entry?.display_name;
  return name != null && name !== "" ? name : code;
}

function isEmptyPlan(plan: ModuleRoutingGraphProps["plan"]): plan is null | Record<string, never> {
  if (plan == null) return true;
  const p = plan as Partial<ModulePlan>;
  const noPrimary = p.primary == null || p.primary === "";
  const noEntries = !Array.isArray(p.entries) || p.entries.length === 0;
  const noSecondary = !Array.isArray(p.secondary) || p.secondary.length === 0;
  return noPrimary && noEntries && noSecondary;
}

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
    return <EmptyState title="No module routing produced" hint="This result contains no primary or secondary module routing information." />;
  }

  const full = plan as ModulePlan;
  const primary = full.primary;
  const secondary = Array.isArray(full.secondary) ? full.secondary : [];
  const entries = Array.isArray(full.entries) ? full.entries : [];
  const entryMap = indexEntries(entries);

  const primaryEntry = primary ? entryMap.get(primary) : undefined;
  const primaryLabel = primary ? nodeLabel(primary, primaryEntry) : "Primary module";

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
      <div style={{ width: "100%", overflowX: "auto" }}>
        <svg
          viewBox={`0 0 ${VIEW_W} ${VIEW_H}`}
          width="100%"
          preserveAspectRatio="xMidYMid meet"
          role="img"
          aria-label="Module routing graph: primary module in the center, secondary modules around it"
          style={{ display: "block", minWidth: 320, maxWidth: "100%" }}
        >
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
        <LegendDot color="var(--primary)" text="Primary module" filled />
        <LegendDot color="var(--accent)" text="Passed" />
        <LegendDot color="var(--warn)" text="Caution" />
        <LegendDot color="var(--danger)" text="Mismatch" />
        <LegendDot color="var(--text-muted)" text="Abstained (dashed)" dashed />
      </div>
    </div>
  );
}

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
