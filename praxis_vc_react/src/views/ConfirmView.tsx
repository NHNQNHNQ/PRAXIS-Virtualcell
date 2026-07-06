import { useEffect, useState } from "react";
import {
  getOptions,
  type CellPreset,
  type Mode,
  type Options,
  type ParseResult,
} from "../api";

// Confirm 页:展示并允许微调 candidate(species/cell_type/perturbation_type/targets),
// 显示 parser/llm_used/schema_valid/assumptions,高亮 missing/errors。
// 铁律:前端不做任何治理/预测判断,仅把用户确认后的 request 原样交给后端执行。
// 出口 onConfirmed 只交出组装好的 request,不再直接 createJob —— run 移到 RunConfirmView。
export default function ConfirmView({
  parseResult,
  onBack,
  onConfirmed,
}: {
  parseResult: ParseResult;
  mode: Mode;
  onBack: () => void;
  onConfirmed: (request: Record<string, unknown>) => void;
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
  const [opts, setOpts] = useState<Options | null>(null);

  useEffect(() => {
    getOptions().then(setOpts).catch(() => setOpts(null)); // 失败静默降级为纯文本
  }, []);

  // 选中预设 → 填充 species/cell_type/perturbation_type/targets(便捷,仍可手改)
  function applyPreset(p: CellPreset) {
    setSpecies(p.species);
    setCellType(p.cell_type);
    if (p.example_perturbation_type) setPertType(p.example_perturbation_type);
    if (p.example_targets) setTargets(p.example_targets.join(", "));
  }

  // 下拉选项:枚举 + 保留当前值(避免锁死非枚举内的历史值)
  function withCurrent(list: string[] | undefined, cur: string): string[] {
    const xs = list ?? [];
    return cur && !xs.includes(cur) ? [cur, ...xs] : xs;
  }

  function confirm() {
    // 以原 candidate 为基底,仅覆盖可编辑字段(保留 request_id/metadata 等)。
    // 只交出组装好的 request,不在此发起 createJob(run 在 RunConfirmView)。
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
    onConfirmed(request);
  }

  return (
    <section className="card">
      <h2>2 · 确认(Confirm)</h2>

      {opts && opts.cell_presets.length > 0 && (
        <label>
          载入 cell 预设(便捷,可再手改)
          <select
            defaultValue=""
            onChange={(e) => {
              const p = opts.cell_presets.find((x) => x.id === e.target.value);
              if (p) applyPreset(p);
            }}
          >
            <option value="">— 选择物种/细胞预设 —</option>
            {opts.cell_presets.map((p) => (
              <option key={p.id} value={p.id}>
                {p.label}
              </option>
            ))}
          </select>
        </label>
      )}

      <div className="grid2">
        <label>
          species
          {opts ? (
            <select value={species} onChange={(e) => setSpecies(e.target.value)}>
              {withCurrent(opts.species, species).map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          ) : (
            <input value={species} onChange={(e) => setSpecies(e.target.value)} />
          )}
        </label>
        <label>
          cell_type(可空)
          <input value={cellType} onChange={(e) => setCellType(e.target.value)} />
        </label>
        <label>
          perturbation_type
          {opts ? (
            <select value={pertType} onChange={(e) => setPertType(e.target.value)}>
              {withCurrent(opts.perturbation_type, pertType).map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          ) : (
            <input value={pertType} onChange={(e) => setPertType(e.target.value)} />
          )}
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

      <div className="row end">
        <button type="button" className="btn btn-ghost" onClick={onBack}>
          ← 返回
        </button>
        <button
          type="button"
          className="btn"
          onClick={confirm}
          disabled={!species.trim()}
        >
          确认(Confirm) →
        </button>
      </div>
    </section>
  );
}
