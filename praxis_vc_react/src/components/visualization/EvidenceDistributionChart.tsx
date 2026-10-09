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

// 证据分布图(spec §4 ③补 / §2 Predictions③:model disagreement / uncertainty)。
// 纯展示、无副作用、不请求数据:数据由 P5 的 PredictionsTab / EvidenceTab 从
// structured_report(model_disagreement + models_used/rejected/failed)提取后传入。
// offline 为 mock 数值时如实展示,不推断真值。配色走 token(不硬编码 hex)。
//   - 分歧度(disagreement)高于阈值(triggered)时,gauge 走 --warn(amber)以示警示;
//     正常态走 --primary/--accent。
//   - 模型计数分布:采纳=--accent/未采纳=--warn/失败=--danger。
// recharts 的 fill 接受 CSS 变量字符串,直接 fill="var(--...)"。
// 文案守 spec §3.5:不外泄 model_disagreement / pairwise_cosine_distance 等原始内部名词,
//   metric 仅作自然化副标签呈现,不当主文案抛给用户。

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

// 分歧度阈值语义:triggered 由后端判定(阈值内部约 0.5),前端只如实呈现,不重算。
const DISAGREEMENT_MAX = 1;

// 模型计数三段:采纳/未采纳/失败,各配 token 色。
type CountDatum = { label: string; value: number; color: string };

export default function EvidenceDistributionChart({
  disagreement,
  models,
}: EvidenceDistributionChartProps) {
  // 入参防御:disagreement / models 可能为 null 或 {}(四输入自检),
  // 先窄化到安全形态,避免访问 .score / .used.length 时崩溃。
  const dis: DisagreementInput = disagreement ?? {};
  const usedArr = Array.isArray(models?.used) ? models.used : [];
  const rejectedArr = Array.isArray(models?.rejected) ? models.rejected : [];
  const failedArr = Array.isArray(models?.failed) ? models.failed : [];

  // 数值缺失容错:score/metric/triggered 用 ?? 兜底。
  const score = dis.score ?? 0;
  const metric = dis.metric ?? "";
  const triggered = dis.triggered ?? false;

  const usedCount = usedArr.length;
  const rejectedCount = rejectedArr.length;
  const failedCount = failedArr.length;

  // 全空(无 score 且三数组皆空)→ EmptyState,不崩。
  const hasScore = dis.score != null;
  const hasModels = usedCount + rejectedCount + failedCount > 0;
  if (!hasScore && !hasModels) {
    return (
      <EmptyState
        title="暂无证据分布"
        hint="此次结果未包含模型分歧度或模型计数。"
      />
    );
  }

  // 分歧度夹取到 [0,1] 供 gauge 定位;文字仍用原值展示。
  const clampedScore = Math.max(0, Math.min(DISAGREEMENT_MAX, score));
  // triggered 时以 warn 高亮,正常态用 primary。
  const gaugeColor = triggered ? "var(--warn)" : "var(--primary)";
  const gaugeData = [{ name: "disagreement", value: clampedScore }];

  const countData: CountDatum[] = [
    { label: "采纳", value: usedCount, color: "var(--accent)" },
    { label: "未采纳", value: rejectedCount, color: "var(--warn)" },
    { label: "失败", value: failedCount, color: "var(--danger)" },
  ];

  // 分歧度的平实副标签:triggered 时提示"分歧偏高",否则"分歧不高";metric 自然化附注。
  const disagreementNote = triggered ? "模型间分歧偏高" : "模型间分歧不高";

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-5)" }}>
      {/* ① 分歧度 gauge(单值 radial,0–1 区间) */}
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
            <span style={{ fontSize: 13, color: "var(--text-muted)" }}>模型分歧度</span>
            <span style={{ fontSize: 14, fontWeight: 600, color: triggered ? "var(--warn)" : "var(--text)" }}>
              {clampedScore.toFixed(2)}
              <span style={{ marginLeft: "var(--space-2)", fontWeight: 500, color: "var(--text-muted)" }}>
                {disagreementNote}
              </span>
            </span>
          </div>
          <div style={{ width: "100%", height: 140 }} aria-label={`模型分歧度 ${clampedScore.toFixed(2)}`}>
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
              基于模型预测向量间的距离度量
            </div>
          )}
        </div>
      )}

      {/* ② 模型计数分布(采纳/未采纳/失败三段计数) */}
      {hasModels && (
        <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-2)" }}>
          <span style={{ fontSize: 13, color: "var(--text-muted)" }}>参与模型分布</span>
          <div style={{ width: "100%", height: 200 }} aria-label="参与模型分布">
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
