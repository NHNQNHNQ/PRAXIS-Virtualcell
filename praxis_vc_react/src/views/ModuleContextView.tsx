import { useEffect, useState } from "react";
import { getModules, getOptions, type CellPreset, type ModuleInfo } from "../api";

// 步骤 4 · 模块预期(Module Context)。
// 挂载时并发拉 8 模块目录(/api/modules)与 cell_presets(/api/options)。
// 按 request.species(+可选 cell_type)匹配 cell preset,取其 modules[] 作"预期模块",
// 在 8 模块目录卡片网格上高亮这些预期模块。
// 铁律 / 关键标注:这是【静态预期】(由 cell preset 声明,不代表实际路由),
// 实际模块路由结果在运行后的结果页(步 6)由后端返回。前端在此不做任何路由判断。
export default function ModuleContextView({
  request,
  onBack,
  onNext,
}: {
  request: Record<string, unknown>;
  onBack: () => void;
  onNext: () => void;
}) {
  const [modules, setModules] = useState<ModuleInfo[] | null>(null); // null=加载中,[]=降级
  const [presets, setPresets] = useState<CellPreset[]>([]);

  useEffect(() => {
    // 失败静默降级为空,不白屏(getModules 失败 → 空目录提示;getOptions 失败 → 无预期高亮)。
    getModules()
      .then((r) => setModules(r.modules))
      .catch(() => setModules([]));
    getOptions()
      .then((o) => setPresets(o.cell_presets))
      .catch(() => setPresets([]));
  }, []);

  const species = request.species == null ? "" : String(request.species);
  const cellType = request.cell_type == null ? "" : String(request.cell_type);

  // 匹配 cell preset:优先 species+cell_type 双命中,否则退化为仅 species 命中。
  const matched =
    presets.find(
      (p) => p.species === species && cellType !== "" && p.cell_type === cellType,
    ) ?? presets.find((p) => p.species === species);

  // 预期模块 code 集合(preset.modules[]);无匹配 preset 或 preset 未声明 modules 则为空集。
  const expected = new Set(matched?.modules ?? []);
  const hasExpectation = expected.size > 0;

  return (
    <section className="card">
      <h2>4 · 模块预期(Module Context)</h2>
      <p className="step-hint">
        下方为 PRAXIS 的模块目录。对当前物种
        {species ? (
          <>
            (<code>{species}</code>
            {cellType ? (
              <>
                {" / "}
                <code>{cellType}</code>
              </>
            ) : null}
            )
          </>
        ) : null}
        ,已根据 cell 预设高亮"预期涉及"的模块。
      </p>

      <div className="note">
        注意:这是<strong>静态预期</strong>(由 cell preset 声明,仅供参考),
        <strong>不代表实际路由</strong>。实际模块路由结果在运行后的结果页(步 6)由后端返回。
      </div>

      {matched == null && species !== "" && (
        <div className="warn">
          未找到物种 <code>{species}</code> 对应的 cell 预设,无静态预期高亮(不影响运行)。
        </div>
      )}

      {modules == null ? (
        <p className="muted">加载中…</p>
      ) : modules.length === 0 ? (
        <div className="warn">模块目录获取失败,已降级(不影响运行,可继续下一步)。</div>
      ) : (
        <div className="module-grid">
          {modules.map((m) => {
            const on = hasExpectation && expected.has(m.code);
            return (
              <div
                key={m.id}
                className={`module-card${on ? " expected" : ""}`}
              >
                <div className="module-card-head">
                  <code className="module-code">{m.code}</code>
                  {on && <span className="module-flag">预期</span>}
                </div>
                <div className="module-name">{m.display_name}</div>
                {m.engines.length > 0 && (
                  <div className="module-engines">
                    engines:{m.engines.join(", ")}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      <div className="row end">
        <button type="button" className="btn btn-ghost" onClick={onBack}>
          ← 返回
        </button>
        <button type="button" className="btn" onClick={onNext}>
          下一步 →
        </button>
      </div>
    </section>
  );
}
