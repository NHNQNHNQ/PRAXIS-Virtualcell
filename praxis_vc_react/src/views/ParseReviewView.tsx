import type { ParseResult } from "../api";

// 步骤 2 · 解析核对(Parse Review)。
// 只读展示后端 /api/parse 的解析结果:candidate_request、parser/llm_used/fallback_used/schema_valid、
// assumptions/missing_fields/errors/clarification。前端不做任何治理/预测判断,仅供用户核对后前进。
export default function ParseReviewView({
  parseResult,
  onBack,
  onNext,
}: {
  parseResult: ParseResult;
  onBack: () => void;
  onNext: () => void;
}) {
  const cand = parseResult.candidate_request;
  // candidate_request 逐字段列成只读表(值为对象/数组时 JSON 序列化)。
  const fields = Object.entries(cand);

  function fmt(v: unknown): string {
    if (v == null) return "—";
    if (Array.isArray(v)) return v.length === 0 ? "[]" : v.join(", ");
    if (typeof v === "object") return JSON.stringify(v);
    return String(v);
  }

  return (
    <section className="card">
      <h2>2 · 解析核对(Parse Review)</h2>
      <p className="step-hint">
        以下为后端解析出的 candidate_request 与元信息,只读核对。确认无误后进入下一步。
      </p>

      <div className="block">
        <h3>candidate_request(候选请求)</h3>
        {fields.length > 0 ? (
          <table className="kv-table">
            <tbody>
              {fields.map(([k, v]) => (
                <tr key={k}>
                  <th>{k}</th>
                  <td>{fmt(v)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="muted">(空)</p>
        )}
      </div>

      <div className="block">
        <h3>解析元信息</h3>
        <ul className="meta">
          <li>
            parser:<code>{parseResult.parser}</code>
          </li>
          <li>
            llm_used:<code>{String(parseResult.llm_used)}</code>
          </li>
          <li>
            fallback_used:<code>{String(parseResult.fallback_used)}</code>
          </li>
          <li>
            schema_valid:
            <code className={parseResult.schema_valid ? "ok" : "bad"}>
              {String(parseResult.schema_valid)}
            </code>
          </li>
        </ul>
      </div>

      {parseResult.assumptions.length > 0 && (
        <div className="note">
          假设(assumptions):{parseResult.assumptions.join(";")}
        </div>
      )}
      {parseResult.missing_fields.length > 0 && (
        <div className="warn">
          缺失字段(missing_fields):{parseResult.missing_fields.join(", ")}
        </div>
      )}
      {parseResult.errors.length > 0 && (
        <div className="bad-box">
          错误(errors):{parseResult.errors.join(";")}
        </div>
      )}
      {parseResult.clarification_required && (
        <div className="warn">需要澄清(clarification_required)。</div>
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
