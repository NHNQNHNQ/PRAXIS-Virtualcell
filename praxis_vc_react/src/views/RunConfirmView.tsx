import { useState } from "react";
import { createJob, type Mode } from "../api";

// 步骤 6 · 运行确认(RunConfirm)。
// 展示最终 request 汇总(只读)+ LLM 报告复选框 + "确认运行"。
// 铁律:前端不做任何治理/预测判断,仅把用户确认后的 request 原样交给后端执行。
// createJob 由此处发起(从 ConfirmView 迁出),保证 confirm→module_context→run_confirm→createJob→result 链不断。

// 最终 request 汇总取值:数组显示为逗号分隔,空值显 "—"。
function fmt(v: unknown): string {
  if (v == null || v === "") return "—";
  if (Array.isArray(v)) return v.length ? v.map(String).join(", ") : "—";
  return String(v);
}

export default function RunConfirmView({
  request,
  mode,
  onBack,
  onRan,
}: {
  request: Record<string, unknown>;
  mode: Mode;
  onBack: () => void;
  onRan: (jobId: string) => void;
}) {
  const [enableLlmReport, setEnableLlmReport] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function run() {
    setBusy(true);
    setErr(null);
    try {
      const ref = await createJob(request, mode, enableLlmReport);
      onRan(ref.job_id);
    } catch (e: unknown) {
      setErr(String(e));
    } finally {
      setBusy(false);
    }
  }

  // 最终 request 汇总的关键字段(只读展示)。
  const summary: [string, unknown][] = [
    ["species", request.species],
    ["cell_type", request.cell_type],
    ["perturbation_type", request.perturbation_type],
    ["perturbation_targets", request.perturbation_targets],
    ["task_type", request.task_type],
  ];

  return (
    <section className="card">
      <h2>6 · 运行确认(Run Confirm)</h2>
      <p className="hero-sub">确认下方请求后运行;解析与预测全在后端确定性 runtime 完成。</p>

      {/* 最终 request 汇总(只读) */}
      <div className="block">
        <h3>最终请求汇总</h3>
        <table className="kv-table">
          <tbody>
            {summary.map(([k, v]) => (
              <tr key={k}>
                <th>{k}</th>
                <td>{fmt(v)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* 完整 request(展开细节) */}
      <details className="block">
        <summary className="muted">查看完整 request JSON</summary>
        <pre className="pretty">{JSON.stringify(request, null, 2)}</pre>
      </details>

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
        <button type="button" className="btn" onClick={run} disabled={busy}>
          {busy ? "运行中…" : "确认运行 →"}
        </button>
      </div>
    </section>
  );
}
