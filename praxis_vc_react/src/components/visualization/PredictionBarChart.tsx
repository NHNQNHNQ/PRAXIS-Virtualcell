import { BarChart, Bar, Cell, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import EmptyState from "../ui/EmptyState";

// 预测柱状图(spec §4 ①②:module response score bar / top predicted changes)。
// 纯展示、无副作用、不请求数据:数据由 P5 各 result tab 从 structured_report 提取后传入。
// offline 为 mock 数值时如实展示,不推断真值。配色走 token(不硬编码 hex)。
//   - 正值柱:--primary;绝对值最大的一根用 --accent 点缀,给一处克制的强调。
//   - 负值柱:--danger。
// recharts 的 fill 接受 CSS 变量字符串,直接 fill="var(--...)"。

type BarDatum = { label: string; value: number };

export type PredictionBarChartProps = {
  data: BarDatum[] | undefined;
  title: string;
  kind: "delta" | "module";
};

// 单根柱的颜色:负值走 danger;绝对值最大的正值点缀 accent;其余正值走 primary。
function barColor(value: number, isPeak: boolean): string {
  if (value < 0) return "var(--danger)";
  if (isPeak) return "var(--accent)";
  return "var(--primary)";
}

export default function PredictionBarChart({ data, title, kind }: PredictionBarChartProps) {
  // 空数据(未传 / null / 非数组 / 空数组)→ 降级到 EmptyState,不崩。
  // 用 Array.isArray 兜底,防非数组(如误传 {})时 .length/.forEach 崩溃。
  if (!Array.isArray(data) || data.length === 0) {
    return (
      <EmptyState
        title={kind === "delta" ? "暂无预测变化" : "暂无模块响应"}
        hint="此次结果未包含可展示的数值。"
      />
    );
  }

  // 找绝对值最大的一根作为 accent 点缀(仅正值参与点缀)。
  let peakIndex = -1;
  let peakAbs = -Infinity;
  data.forEach((d, i) => {
    // 仅严格正值参与 accent 点缀:全零/全负数据集不给零柱误点缀强调绿。
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
