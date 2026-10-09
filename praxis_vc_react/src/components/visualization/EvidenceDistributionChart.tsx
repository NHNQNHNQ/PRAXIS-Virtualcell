import {
  BarChart,
  Bar,
  Cell,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  RadialBarChart,
  RadialBar,
  PolarAngleAxis,
} from "recharts";
import EmptyState from "../ui/EmptyState";


type DisagreementInput = {
  score?: number;
  metric?: string;
  triggered?: boolean;
};

type ModelsInput = {
  used: string[];
  rejected: string[];
  failed: string[];
};

export type EvidenceDistributionChartProps = {
  disagreement: DisagreementInput;
  models: ModelsInput;
};

const DISAGREEMENT_MAX = 1;

type CountDatum = { label: string; value: number; color: string };

export default function EvidenceDistributionChart({
  disagreement,
  models,
}: EvidenceDistributionChartProps) {
  const dis: DisagreementInput = disagreement ?? {};
  const usedArr = Array.isArray(models?.used) ? models.used : [];
  const rejectedArr = Array.isArray(models?.rejected) ? models.rejected : [];
  const failedArr = Array.isArray(models?.failed) ? models.failed : [];

  const score = dis.score ?? 0;
  const metric = dis.metric ?? "";
  const triggered = dis.triggered ?? false;

  const usedCount = usedArr.length;
  const rejectedCount = rejectedArr.length;
  const failedCount = failedArr.length;

  const hasScore = dis.score != null;
  const hasModels = usedCount + rejectedCount + failedCount > 0;
  if (!hasScore && !hasModels) {
    return (
      <EmptyState
        title="No evidence distribution available"
        hint="This result contains no model disagreement score or model counts."
      />
    );
  }

  const clampedScore = Math.max(0, Math.min(DISAGREEMENT_MAX, score));
  const gaugeColor = triggered ? "var(--warn)" : "var(--primary)";
  const gaugeData = [{ name: "disagreement", value: clampedScore }];

  const countData: CountDatum[] = [
    { label: "Used", value: usedCount, color: "var(--accent)" },
    { label: "Rejected", value: rejectedCount, color: "var(--warn)" },
    { label: "Failed", value: failedCount, color: "var(--danger)" },
  ];

  const disagreementNote = triggered ? "High model disagreement" : "Model disagreement is not high";

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-5)" }}>
      {hasScore && (
        <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-2)" }}>
          <div
            style={{
              display: "flex",
              alignItems: "baseline",
              justifyContent: "space-between",
              gap: "var(--space-3)",
            }}
          >
            <span style={{ fontSize: 13, color: "var(--text-muted)" }}>Model disagreement</span>
            <span style={{ fontSize: 14, fontWeight: 600, color: triggered ? "var(--warn)" : "var(--text)" }}>
              {clampedScore.toFixed(2)}
              <span style={{ marginLeft: "var(--space-2)", fontWeight: 500, color: "var(--text-muted)" }}>
                {disagreementNote}
              </span>
            </span>
          </div>
          <div style={{ width: "100%", height: 140 }} aria-label={`Model disagreement ${clampedScore.toFixed(2)}`}>
            <ResponsiveContainer width="100%" height="100%">
              <RadialBarChart
                data={gaugeData}
                startAngle={210}
                endAngle={-30}
                innerRadius="66%"
                outerRadius="100%"
                barSize={14}
              >
                <PolarAngleAxis
                  type="number"
                  domain={[0, DISAGREEMENT_MAX]}
                  angleAxisId={0}
                  tick={false}
                />
                <RadialBar
                  dataKey="value"
                  cornerRadius={7}
                  background={{ fill: "var(--code-bg)" }}
                  fill={gaugeColor}
                  isAnimationActive={false}
                />
              </RadialBarChart>
            </ResponsiveContainer>
          </div>
          {metric !== "" && (
            <div style={{ fontSize: 12, color: "var(--text-muted)", textAlign: "center" }}>
              Measured from distances between model prediction vectors
            </div>
          )}
        </div>
      )}

      {hasModels && (
        <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-2)" }}>
          <span style={{ fontSize: 13, color: "var(--text-muted)" }}>Participating model distribution</span>
          <div style={{ width: "100%", height: 200 }} aria-label="Participating model distribution">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={countData} margin={{ top: 8, right: 12, bottom: 8, left: 4 }}>
                <XAxis
                  dataKey="label"
                  tick={{ fill: "var(--text-muted)", fontSize: 12 }}
                  axisLine={{ stroke: "var(--border)" }}
                  tickLine={false}
                  interval={0}
                />
                <YAxis
                  allowDecimals={false}
                  tick={{ fill: "var(--text-muted)", fontSize: 12 }}
                  axisLine={{ stroke: "var(--border)" }}
                  tickLine={false}
                  width={32}
                />
                <Tooltip
                  cursor={{ fill: "var(--code-bg)" }}
                  contentStyle={{
                    background: "var(--surface)",
                    border: "1px solid var(--border)",
                    borderRadius: "var(--radius-sm)",
                    color: "var(--text)",
                    fontSize: 12,
                  }}
                />
                <Bar dataKey="value" radius={[3, 3, 0, 0]} isAnimationActive={false}>
                  {countData.map((d) => (
                    <Cell key={d.label} fill={d.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </div>
  );
}
