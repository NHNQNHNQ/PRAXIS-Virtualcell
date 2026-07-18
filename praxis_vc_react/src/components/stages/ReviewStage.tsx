import { useEffect, useMemo, useState } from "react";
import {
  getOptions,
  type CellPreset,
  type Options,
  type ParseResult,
} from "../../api";
import Card from "../ui/Card";
import FieldRow from "../ui/FieldRow";
import Button from "../ui/Button";
import type { FieldStatus } from "../ui/StatusPill";

// Stage 2 · Review(spec §2,最重要)—— 核对任务解读 + 可编辑分组表单。
// 合并旧两步:上部解析摘要(只读元信息 + 假设/缺失)+ 下部可编辑分组表单。
// 迁自:
//   · ParseReviewView —— parser/llm_used/fallback_used/schema_valid 元信息、assumptions/missing/errors/clarification 展示;
//   · ConfirmView —— cell 预设 applyPreset、species/cell_type/perturbation_type/targets 编辑、withCurrent 组装、
//     以 candidate_request 为基底覆盖可编辑字段(保留 request_id/metadata),confirm 出口只交出组装好的 request。
// 铁律(红线):前端只组装/展示,绝不做任何治理/预测/科学裁决判断;元信息如实展示。
//
// 字段初值来源(修掉 P2 桥接的 remount seed 限制):
//   initialRequest(= job.confirmedRequest)非空 → 从它回填(保留用户上次编辑值,回退再进不丢);
//   否则 → 从 parsedIntent.candidate_request seed。

// 从来源对象读取可编辑字段的字符串初值(数组按逗号拼接)。
function readStr(src: Record<string, unknown>, key: string): string {
  const v = src[key];
  if (v == null) return "";
  if (Array.isArray(v)) return v.join(", ");
  return String(v);
}

export default function ReviewStage({
  parsedIntent,
  initialRequest,
  onConfirmed,
  onBack,
}: {
  parsedIntent: ParseResult;
  initialRequest: Record<string, unknown> | null;
  onConfirmed: (request: Record<string, unknown>) => void;
  onBack: () => void;
}) {
  // 候选请求(解析结果)始终作为基底,承载 request_id/metadata/task_type 等非编辑字段。
  const cand = parsedIntent.candidate_request as Record<string, unknown>;
  // 可编辑字段的种子:优先用户上次编辑值(initialRequest),否则解析候选。
  const seed = initialRequest ?? cand;

  const [species, setSpecies] = useState(() => readStr(seed, "species"));
  const [cellType, setCellType] = useState(() => readStr(seed, "cell_type"));
  const [pertType, setPertType] = useState(() =>
    readStr(seed, "perturbation_type"),
  );
  const [targets, setTargets] = useState(() =>
    readStr(seed, "perturbation_targets"),
  );
  const [opts, setOpts] = useState<Options | null>(null);

  useEffect(() => {
    getOptions().then(setOpts).catch(() => setOpts(null)); // 失败静默降级为纯文本输入
  }, []);

  // 选中预设 → 填充 species/cell_type/perturbation_type/targets(便捷,仍可手改)。迁自 ConfirmView.applyPreset。
  function applyPreset(p: CellPreset) {
    setSpecies(p.species);
    setCellType(p.cell_type);
    if (p.example_perturbation_type) setPertType(p.example_perturbation_type);
    if (p.example_targets) setTargets(p.example_targets.join(", "));
  }

  // 下拉选项:枚举 + 保留当前值(避免锁死非枚举内的历史值)。迁自 ConfirmView.withCurrent。
  function withCurrent(list: string[] | undefined, cur: string): string[] {
    const xs = list ?? [];
    return cur && !xs.includes(cur) ? [cur, ...xs] : xs;
  }

  // 字段状态映射(spec §2 / 计划 Task 9.9 Step4):状态点须随【当前编辑值】实时反映,
  // 而非停留在最初的静态解析结果。综合判定 = 当前编辑值 + 原始解析信号(missing_fields / assumptions):
  //   · 当前值非空 → 若该字段来自推断(assumptions 提及)则 inferred,否则 confirmed(已确认);
  //   · 当前值为空 → 若命中 missing_fields 则 missing(红橙缺失),否则 editable(可编辑)。
  // 关键:值非空即不再判 missing,故 species 从空→选 human 后 StatusPill 由「缺失」变「已确认」。
  // 仍只看解析信号 + 编辑值,不做任何科学裁决。
  const missingSet = useMemo(
    () => new Set(parsedIntent.missing_fields),
    [parsedIntent.missing_fields],
  );
  // assumptions 是一组自然语言句子;某字段被推断则其字段名通常出现在假设文本里。
  const assumptionsText = useMemo(
    () => parsedIntent.assumptions.join(" ").toLowerCase(),
    [parsedIntent.assumptions],
  );

  // 单个可编辑字段的状态:先看当前编辑值有无,再叠加原始解析信号。
  function statusOf(key: string, value: string): FieldStatus {
    if (value.trim()) {
      // 有值:来自推断的仍标 inferred(便于审阅),否则视为已确认。
      return assumptionsText.includes(key) ? "inferred" : "confirmed";
    }
    // 无值:命中 missing_fields → 缺失(红橙提示),否则可编辑。
    return missingSet.has(key) ? "missing" : "editable";
  }

  // 组装 request:以 candidate_request 为基底覆盖可编辑字段,保留 request_id/metadata 等。
  // 迁自 ConfirmView.confirm——只交出组装好的 request,不在此发起运行。
  function confirm() {
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

  // 请求输出(只读):task_type 等来自候选,不在此编辑。
  const taskType = readStr(cand, "task_type");

  return (
    <section style={{ maxWidth: "820px" }}>
      {/* 标题区:平实说明,非工程旁白(spec §3.5)。 */}
      <div style={{ marginBottom: "var(--space-5)" }}>
        <h1
          style={{
            fontFamily: "var(--font-display)",
            fontSize: "28px",
            fontWeight: 500,
            lineHeight: 1.15,
            letterSpacing: "-0.01em",
            color: "var(--text)",
            margin: 0,
          }}
        >
          核对任务解读
        </h1>
        <p
          style={{
            marginTop: "var(--space-3)",
            fontSize: "14px",
            lineHeight: 1.55,
            color: "var(--text-muted)",
            maxWidth: "62ch",
          }}
        >
          下面是系统对你所描述实验的理解。请核对生物体系与扰动设置,必要时直接修改;
          确认无误后即可继续。运行前的这一步是为了让任务定义可审阅。
        </p>
      </div>

      {/* 分组卡 1:生物系统 —— species / cell_type + cell 预设载入。 */}
      <Card title="生物系统">
        {opts && opts.cell_presets.length > 0 && (
          <div style={{ marginBottom: "var(--space-3)" }}>
            <label
              style={{
                display: "flex",
                flexDirection: "column",
                gap: "var(--space-1)",
                fontSize: "13px",
                color: "var(--text-muted)",
                maxWidth: "360px",
              }}
            >
              载入常用体系(可再手改)
              <select
                defaultValue=""
                onChange={(e) => {
                  const p = opts.cell_presets.find((x) => x.id === e.target.value);
                  if (p) applyPreset(p);
                }}
              >
                <option value="">— 选择物种 / 细胞类型 —</option>
                {opts.cell_presets.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.label}
                  </option>
                ))}
              </select>
            </label>
          </div>
        )}

        <FieldRow label="物种" status={statusOf("species", species)}>
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
        </FieldRow>

        <FieldRow
          label="细胞类型（可留空）"
          status={cellType.trim() ? "confirmed" : "editable"}
        >
          <input value={cellType} onChange={(e) => setCellType(e.target.value)} />
        </FieldRow>
      </Card>

      {/* 分组卡 2:扰动 —— perturbation_type / perturbation_targets。 */}
      <Card title="扰动">
        <FieldRow
          label="扰动类型"
          status={statusOf("perturbation_type", pertType)}
        >
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
        </FieldRow>

        <FieldRow
          label="扰动对象（逗号分隔）"
          status={statusOf("perturbation_targets", targets)}
        >
          <input
            value={targets}
            onChange={(e) => setTargets(e.target.value)}
            placeholder="例:AHR, TP53"
          />
        </FieldRow>
      </Card>

      {/* 分组卡 3:请求输出 —— task_type 等(只读)。 */}
      <Card title="请求输出">
        <FieldRow label="任务类型" status="locked">
          <span style={{ fontSize: "14px", color: "var(--text)" }}>
            {taskType || "—"}
          </span>
        </FieldRow>
      </Card>

      {/* 分组卡 4:任务理解与假设 —— 主流程说人话(§3.5),精确/审计术语下沉 Stage 5。 */}
      <Card title="任务理解与假设">
        <ul className="meta" style={{ marginTop: 0 }}>
          <li>
            解读方式:
            <code>
              {parsedIntent.parser.toLowerCase().includes("llm")
                ? "语言模型辅助"
                : "确定性关键词"}
            </code>
          </li>
          <li>
            语言模型参与:<code>{parsedIntent.llm_used ? "是" : "否"}</code>
          </li>
        </ul>

        {parsedIntent.assumptions.length > 0 && (
          <div className="note">
            推断的假设:{parsedIntent.assumptions.join(";")}
          </div>
        )}
        {parsedIntent.missing_fields.length > 0 && (
          <div className="warn">
            尚缺信息:{parsedIntent.missing_fields.join(", ")}
          </div>
        )}
        {parsedIntent.errors.length > 0 && (
          <div className="err">
            解读时的问题:{parsedIntent.errors.join(";")}
          </div>
        )}
        {parsedIntent.clarification_required && (
          <div className="warn">这项描述还需进一步澄清后再运行。</div>
        )}
      </Card>

      {/* 操作行:返回上一步 / 确认继续。disabled 规则等价旧 Confirm(species 必填)。 */}
      <div
        style={{
          display: "flex",
          justifyContent: "flex-end",
          gap: "var(--space-2)",
          marginTop: "var(--space-4)",
        }}
      >
        <Button variant="ghost" onClick={onBack}>
          ← 返回
        </Button>
        <Button onClick={confirm} disabled={!species.trim()}>
          确认并继续 →
        </Button>
      </div>
    </section>
  );
}
