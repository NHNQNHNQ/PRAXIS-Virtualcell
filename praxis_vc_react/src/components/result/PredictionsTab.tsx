import type { ReportResult } from "../../api";
import Card from "../ui/Card";
import EmptyState from "../ui/EmptyState";
import {
  PredictionBarChart,
  ReliabilityMeter,
  EvidenceDistributionChart,
} from "../visualization";

// Stage 5 · Predictions tab(spec §2 Predictions / §4 / §3.5)——用 P4 已建的只读可视化组件
// 把 structured_report 的预测三块画出来:
//   ① Δgene top changes  → PredictionBarChart(kind="delta")
//   ② module/pathway response → PredictionBarChart(kind="module")（mock 结构里暂无此字段,
//      有则整形展示,无则不渲染,不脑补)
//   ③ 结果可靠性 → ReliabilityMeter(learned_reliability.reliability_score)
//   ④ 模型分歧 / 参与模型分布 → EvidenceDistributionChart(model_disagreement + models_*)
//
// 铁律(§Phase9 红线):前端只读展示,不做预测/治理裁决;offline 为 mock 数值时如实展示,
// 数值不足就少画/走空态,绝不推断或伪造真值(尤其不为裸 delta 数组编造真实基因名)。
// 数值取自与「报告」tab 相同的 structured_report,保证两处一致。配色走 token(组件内已守)。

// ── 安全取值助手(structured_report 是后端 Record,字段可能缺失)──
function g(obj: Record<string, unknown>, key: string): unknown {
  return obj?.[key];
}
function asRecord(v: unknown): Record<string, unknown> {
  return v != null && typeof v === "object" && !Array.isArray(v)
    ? (v as Record<string, unknown>)
    : {};
}
function asStrArr(v: unknown): string[] {
  return Array.isArray(v) ? v.map((x) => String(x)) : [];
}
// 只接受有限数值:过滤掉 null/NaN/非数字项,避免图里出现空柱或 NaN。
function asNumArr(v: unknown): number[] {
  if (!Array.isArray(v)) return [];
  return v.filter((x): x is number => typeof x === "number" && Number.isFinite(x));
}

type BarDatum = { label: string; value: number };

// Δ 列表整形:mock 的 prediction.delta 是裸数值数组(无基因名)。
// 取绝对值最大的 top N,标签用「Δ{序号}」占位——不臆造真实基因名(红线)。
// 若未来 .53 的 prediction 带 {gene, delta} 结构,这里用 label 字段承载真实基因名。
function shapeDelta(prediction: unknown, topN = 12): BarDatum[] {
  const pred = asRecord(prediction);

  // 形态 A:带基因名的对象列表 [{gene?/label?/name?, delta?/value?}]
  if (Array.isArray(pred.delta) && pred.delta.some((d) => d != null && typeof d === "object")) {
    const rows: BarDatum[] = [];
    for (const item of pred.delta as unknown[]) {
      const r = asRecord(item);
      const rawV = r.delta ?? r.value ?? r.log2fc ?? r.score;
      if (typeof rawV !== "number" || !Number.isFinite(rawV)) continue;
      const rawL = r.gene ?? r.label ?? r.name ?? r.target;
      const label = rawL != null ? String(rawL) : `Δ${rows.length + 1}`;
      rows.push({ label, value: rawV });
    }
    return topByAbs(rows, topN);
  }

  // 形态 B(当前 mock):裸数值数组 → 用序号占位标签,不伪造基因名。
  const nums = asNumArr(pred.delta);
  const rows: BarDatum[] = nums.map((v, i) => ({ label: `Δ${i + 1}`, value: v }));
  return topByAbs(rows, topN);
}

// module/pathway response score 整形:mock 结构里暂无此字段,故正常返回 [](不渲染)。
// 若结构里出现 module_response / pathway_response(数组或 {name:score} 映射)则整形,不脑补。
function shapeModuleResponse(sr: Record<string, unknown>, topN = 12): BarDatum[] {
  const raw = g(sr, "module_response") ?? g(sr, "pathway_response") ?? g(sr, "module_scores");

  // 数组形态:[{module?/name?/label?, score?/value?}]
  if (Array.isArray(raw)) {
    const rows: BarDatum[] = [];
    for (const item of raw as unknown[]) {
      const r = asRecord(item);
      const rawV = r.score ?? r.value ?? r.response;
      if (typeof rawV !== "number" || !Number.isFinite(rawV)) continue;
      const rawL = r.module ?? r.name ?? r.label;
      rows.push({ label: rawL != null ? String(rawL) : `M${rows.length + 1}`, value: rawV });
    }
    return topByAbs(rows, topN);
  }

  // 映射形态:{ moduleName: score }
  const rec = asRecord(raw);
  const rows: BarDatum[] = [];
  for (const [k, v] of Object.entries(rec)) {
    if (typeof v === "number" && Number.isFinite(v)) rows.push({ label: k, value: v });
  }
  return topByAbs(rows, topN);
}

// 按绝对值降序取前 topN(强调最显著的变化)。
function topByAbs(rows: BarDatum[], topN: number): BarDatum[] {
  return [...rows]
    .sort((a, b) => Math.abs(b.value) - Math.abs(a.value))
    .slice(0, topN);
}

export default function PredictionsTab({ report }: { report: ReportResult }) {
  const sr = report.structured_report ?? {};

  // abstain:结构里 abstain=true 或 learned_reliability.abstain_decision === "abstain"。
  const learned = asRecord(g(sr, "learned_reliability"));
  const abstainFlag = Boolean(g(sr, "abstain"));
  const abstainDecision = String(learned.abstain_decision ?? "");
  const abstained = abstainFlag || abstainDecision === "abstain";

  // 预测缺失:abstain 时后端把 prediction 置 None(见 report.py);此时无预测可画。
  const prediction = g(sr, "prediction");
  const hasPrediction = prediction != null;

  // 整形(容错):数值不足则各图自带空态,不脑补。
  const deltaData = shapeDelta(prediction);
  const moduleData = shapeModuleResponse(sr);

  // reliability_score:learned_reliability.reliability_score(与「报告」tab 同源)。
  const rawScore = learned.reliability_score;
  const reliabilityScore =
    typeof rawScore === "number" && Number.isFinite(rawScore) ? rawScore : null;
  const reliabilityMode = String(learned.reliability_mode ?? "");
  const reliabilityLabel = String(g(sr, "reliability") ?? "");

  // 模型分歧 + 参与模型分布(与 EvidenceDistributionChart 的入参形态对齐)。
  const dis = asRecord(g(sr, "model_disagreement"));
  const disagreement = {
    score: typeof dis.score === "number" ? dis.score : undefined,
    metric: dis.metric != null ? String(dis.metric) : undefined,
    triggered: typeof dis.triggered === "boolean" ? dis.triggered : undefined,
  };
  const models = {
    used: asStrArr(g(sr, "models_used")),
    rejected: asStrArr(g(sr, "models_rejected")),
    failed: asStrArr(g(sr, "models_failed")),
  };

  // abstain 或完全无预测数据(prediction 缺失且无 Δ)→ 整页降级到 EmptyState。
  if (abstained || (!hasPrediction && deltaData.length === 0 && moduleData.length === 0)) {
    return (
      <EmptyState
        title={abstained ? "已 abstain,无预测结果" : "暂无预测结果"}
        hint={
          abstained
            ? "本次未给出预测结论;可靠性判定与原因见「报告」。"
            : "此次结果未包含可展示的预测数值。"
        }
      />
    );
  }

  const stackStyle = {
    display: "flex",
    flexDirection: "column" as const,
    gap: "var(--space-4)",
  };

  return (
    <div style={stackStyle}>
      {/* ① Δ top changes(裸 delta 数组按序号标注,不伪造基因名) */}
      <Card title="预测变化(Δ）">
        <PredictionBarChart data={deltaData} title="预测变化 Δ（top）" kind="delta" />
        <div style={{ fontSize: 12, color: "var(--text-muted)", marginTop: "var(--space-2)" }}>
          柱高为各维度的预测变化量（Δ）；标签为维度序号，非基因名。
        </div>
      </Card>

      {/* ② module/pathway response(mock 无此字段时不渲染该卡,不脑补) */}
      {moduleData.length > 0 && (
        <Card title="模块响应强度">
          <PredictionBarChart data={moduleData} title="模块响应强度" kind="module" />
        </Card>
      )}

      {/* ③ 结果可靠性 */}
      <Card title="结果可靠性">
        <ReliabilityMeter
          score={reliabilityScore}
          mode={reliabilityMode}
          reliability={reliabilityLabel}
        />
      </Card>

      {/* ④ 模型分歧 / 参与模型分布 */}
      <Card title="模型证据分布">
        <EvidenceDistributionChart disagreement={disagreement} models={models} />
      </Card>
    </div>
  );
}
