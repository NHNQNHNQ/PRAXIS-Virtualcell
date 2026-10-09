import type { ReportResult } from "../../api";
import Card from "../ui/Card";
import EmptyState from "../ui/EmptyState";
import {
  PredictionBarChart,
  ReliabilityMeter,
  EvidenceDistributionChart,
} from "../visualization";

//   ① Δgene top changes  → PredictionBarChart(kind="delta")
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
function asNumArr(v: unknown): number[] {
  if (!Array.isArray(v)) return [];
  return v.filter((x): x is number => typeof x === "number" && Number.isFinite(x));
}

type BarDatum = { label: string; value: number };

function shapeDelta(prediction: unknown, topN = 12): BarDatum[] {
  const pred = asRecord(prediction);

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

  const nums = asNumArr(Array.isArray(pred.delta) ? pred.delta : pred.values);
  const rows: BarDatum[] = nums.map((v, i) => ({ label: `Δ${i + 1}`, value: v }));
  return topByAbs(rows, topN);
}

function shapeModuleResponse(sr: Record<string, unknown>, topN = 12): BarDatum[] {
  const raw = g(sr, "module_response") ?? g(sr, "pathway_response") ?? g(sr, "module_scores");

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

  const rec = asRecord(raw);
  const rows: BarDatum[] = [];
  for (const [k, v] of Object.entries(rec)) {
    if (typeof v === "number" && Number.isFinite(v)) rows.push({ label: k, value: v });
  }
  return topByAbs(rows, topN);
}

function topByAbs(rows: BarDatum[], topN: number): BarDatum[] {
  return [...rows]
    .sort((a, b) => Math.abs(b.value) - Math.abs(a.value))
    .slice(0, topN);
}

export default function PredictionsTab({ report }: { report: ReportResult }) {
  const sr = report.structured_report ?? {};

  const learned = asRecord(g(sr, "learned_reliability"));
  const abstainFlag = Boolean(g(sr, "abstain"));
  const abstainDecision = String(learned.abstain_decision ?? "");
  const abstained = abstainFlag || abstainDecision === "abstain";

  const prediction = g(sr, "prediction");
  const hasPrediction = prediction != null;
  const predictionRecord = asRecord(prediction);
  const valueCount = asNumArr(predictionRecord.values).length;
  const projectionMetadata = asRecord(predictionRecord.projection_metadata);

  const deltaData = shapeDelta(prediction);
  const moduleData = shapeModuleResponse(sr);

  const rawScore = learned.reliability_score;
  const reliabilityScore =
    typeof rawScore === "number" && Number.isFinite(rawScore) ? rawScore : null;
  const reliabilityMode = String(learned.reliability_mode ?? "");
  const reliabilityLabel = String(g(sr, "reliability") ?? "");

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

  if (abstained || (!hasPrediction && deltaData.length === 0 && moduleData.length === 0)) {
    return (
      <EmptyState
        title={abstained ? "No prediction was produced" : "No predictions available"}
        hint={
          abstained
            ? "See Report for the reliability decision and reasons."
            : "This result contains no predicted values to display."
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
      <Card title="Predicted change (Δ)">
        <PredictionBarChart data={deltaData} title="Predicted change Δ (top)" kind="delta" />
        <div style={{ fontSize: 12, color: "var(--text-muted)", marginTop: "var(--space-2)" }}>
          Bar height shows the predicted change (Δ) for each dimension. Labels are dimension indices, not gene names.
          {valueCount > 0 && (
            <>
              {" "}Full output contains {valueCount.toLocaleString("en-US")} dimensions; feature identity:
              <code>{String(projectionMetadata.feature_ids_sha256 ?? "—")}</code>.
            </>
          )}
        </div>
      </Card>

      {moduleData.length > 0 && (
        <Card title="Module response strength">
          <PredictionBarChart data={moduleData} title="Module response strength" kind="module" />
        </Card>
      )}

      <Card title="Result reliability">
        <ReliabilityMeter
          score={reliabilityScore}
          mode={reliabilityMode}
          reliability={reliabilityLabel}
        />
      </Card>

      <Card title="Model evidence distribution">
        <EvidenceDistributionChart disagreement={disagreement} models={models} />
      </Card>
    </div>
  );
}
