import { BarChart, Bar, Cell, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import EmptyState from "../ui/EmptyState";


type BarDatum = { label: string; value: number };

export type PredictionBarChartProps = {
  data: BarDatum[] | undefined;
  title: string;
  kind: "delta" | "module";
};

function barColor(value: number, isPeak: boolean): string {
  if (value < 0) return "var(--danger)";
  if (isPeak) return "var(--accent)";
  return "var(--primary)";
}

export default function PredictionBarChart({ data, title, kind }: PredictionBarChartProps) {
  if (!Array.isArray(data) || data.length === 0) {
    return (
      <EmptyState
        title={kind === "delta" ? "No predicted changes available" : "No module response available"}
        hint="This result contains no values to display."
      />
    );
  }

  let peakIndex = -1;
  let peakAbs = -Infinity;
  data.forEach((d, i) => {
    if (d.value > 0 && Math.abs(d.value) > peakAbs) {
      peakAbs = Math.abs(d.value);
      peakIndex = i;
    }
  });

  return (
    <div style={{ width: "100%", height: 240 }} aria-label={title}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 8, right: 12, bottom: 8, left: 4 }}>
          <XAxis
            dataKey="label"
            tick={{ fill: "var(--text-muted)", fontSize: 12 }}
            axisLine={{ stroke: "var(--border)" }}
            tickLine={false}
            interval={0}
          />
          <YAxis
            tick={{ fill: "var(--text-muted)", fontSize: 12 }}
            axisLine={{ stroke: "var(--border)" }}
            tickLine={false}
            width={44}
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
            {data.map((d, i) => (
              <Cell key={`${d.label}-${i}`} fill={barColor(d.value, i === peakIndex)} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
