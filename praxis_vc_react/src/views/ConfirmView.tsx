import { useState } from "react";
import { createJob, type Mode, type ParseResult } from "../api";

// Confirm 页:展示并允许微调 candidate(species/cell_type/perturbation_type/targets),
// 显示 parser/llm_used/schema_valid/assumptions,高亮 missing/errors。
// 铁律:前端不做任何治理/预测判断,仅把用户确认后的 request 原样交给后端执行。
export default function ConfirmView({
  parseResult,
  mode,
  onBack,
  onRan,
}: {
  parseResult: ParseResult;
  mode: Mode;
  onBack: () => void;
  onRan: (jobId: string) => void;
}) {
  const cand = parseResult.candidate_request as Record<string, unknown>;
  const [species, setSpecies] = useState(String(cand.species ?? ""));
  const [cellType, setCellType] = useState(
    cand.cell_type == null ? "" : String(cand.cell_type),
  );
  const [pertType, setPertType] = useState(String(cand.perturbation_type ?? ""));
  const [targets, setTargets] = useState(
    Array.isArray(cand.perturbation_targets)
      ? (cand.perturbation_targets as unknown[]).join(", ")
      : "",
  );
  const [enableLlmReport, setEnableLlmReport] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function run() {
    setBusy(true);
    setErr(null);
    // 以原 candidate 为基底,仅覆盖可编辑字段(保留 request_id/metadata 等)。
    const request: Record<string, unknown> = {
      ...cand,
      species,
      cell_type: cellType.trim() === "" ? null : cellType.trim(),
      perturbation_type: pertType,
      perturbation_targets: targets
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean),
    };
    try {
      const ref = await createJob(request, mode, enableLlmReport);
      onRan(ref.job_id);
    } catch (e: unknown) {
      setErr(String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="card">
      <h2>2 · 确认(Confirm)</h2>

      <div className="grid2">
        <label>
          species
          <input value={species} onChange={(e) => setSpecies(e.target.value)} />
        </label>
        <label>
          cell_type(可空)
          <input value={cellType} onChange={(e) => setCellType(e.target.value)} />
        </label>
        <label>
          perturbation_type
          <input value={pertType} onChange={(e) => setPertType(e.target.value)} />
        </label>
        <label>
          perturbation_targets(逗号分隔)
          <input value={targets} onChange={(e) => setTargets(e.target.value)} />
        </label>
      </div>

      <ul className="meta">
        <li>parser:<code>{parseResult.parser}</code></li>
        <li>llm_used:<code>{String(parseResult.llm_used)}</code></li>
        <li>fallback_used:<code>{String(parseResult.fallback_used)}</code></li>
        <li>
          schema_valid:
          <code className={parseResult.schema_valid ? "ok" : "bad"}>
            {String(parseResult.schema_valid)}
          </code>
        </li>
      </ul>

      {parseResult.assumptions.length > 0 && (
        <div className="note">
          假设(assumptions):{parseResult.assumptions.join(";")}
        </div>
      )}
      {parseResult.missing_fields.length > 0 && (
        <div className="warn">缺失字段(missing):{parseResult.missing_fields.join(", ")}</div>
      )}
      {parseResult.errors.length > 0 && (
        <div className="bad-box">错误(errors):{parseResult.errors.join(";")}</div>
      )}
      {parseResult.clarification_required && (
        <div className="warn">需要澄清(clarification_required)。</div>
      )}

      <label className="checkbox">
        <input
          type="checkbox"
          checked={enableLlmReport}
          onChange={(e) => setEnableLlmReport(e.target.checked)}
        />
        生成 LLM 叙述报告(仅改写措辞,不参与预测/治理决策)
      </label>

      {err && <pre className="err">{err}</pre>}

      <div className="row end">
        <button type="button" className="btn btn-ghost" onClick={onBack} disabled={busy}>
          ← 返回
        </button>
        <button type="button" className="btn" onClick={run} disabled={busy || !species.trim()}>
          {busy ? "运行中…" : "Confirm and Run →"}
        </button>
      </div>
    </section>
  );
}
