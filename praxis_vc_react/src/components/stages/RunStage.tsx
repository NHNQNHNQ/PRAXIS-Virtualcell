import { useEffect, useRef, useState } from "react";
import {
  createJob,
  type Mode,
  type ModulePlan,
  type RunStatus,
} from "../../api";
import Card from "../ui/Card";
import Button from "../ui/Button";
import Badge from "../ui/Badge";

// Stage 4 · Run(spec §2 Stage4 "运行前确认 / 即将运行的实验")。
// 迁自 views/RunConfirmView:最终请求汇总(只读)+ 完整 request JSON 折叠 + 文字解读开关 + createJob 调用。
// 在此基础上加 spec §2 的 execution manifest 风格(预期模块)与"确定性步骤指示"。
//
// 🔴 红线 4(核心):后端 /api/jobs(createJob)是【同步执行】——一次 await 即拿 job_id,
// 并非流式/分步返回。因此下面的"运行进度"是【确定性步骤指示】:一组固定文案序列
// (核对输入→确定物种→匹配模块→运行预测→安全与可靠性检查→汇总解读→留存记录),
// 由前端定时器逐步点亮,纯属示意,【非真流式,也不轮询后端 job 状态制造流式假象】。
// 真实的逐步执行轨迹(32 步 trace)在结果页的「运行轨迹」中查看,本阶段不显示真实 trace。
//
// 铁律:前端不做任何治理/预测判断,仅把用户确认后的 request 原样交给后端同步执行。

// 汇总取值:数组显示为逗号分隔,空值显 "—"。
function fmt(v: unknown): string {
  if (v == null || v === "") return "—";
  if (Array.isArray(v)) return v.length ? v.map(String).join(", ") : "—";
  return String(v);
}

// 确定性步骤指示的固定文案序列(平实中文,§3.5;不外泄 dispatch/manifest/provenance 等内部名词)。
// 【非真流式】:这只是标准执行步骤的示意清单,不对应后端的分步回调。
const RUN_STEPS = [
  "核对输入",
  "确定物种背景",
  "匹配相关模块",
  "运行预测模型",
  "安全与可靠性检查",
  "汇总结果解读",
  "留存运行记录",
] as const;

// 逐步点亮的时间间隔(ms)。纯前端节奏,与后端返回时机无关。
const STEP_INTERVAL_MS = 450;

export default function RunStage({
  request,
  mode,
  onRan,
  onBack,
  setRunStatus,
  modulePlan,
}: {
  request: Record<string, unknown>;
  mode: Mode;
  onRan: (jobId: string) => void;
  onBack: () => void;
  setRunStatus: (s: RunStatus) => void;
  modulePlan?: ModulePlan | null;
}) {
  const [enableLlmReport, setEnableLlmReport] = useState(false);
  const [running, setRunning] = useState(false); // 本地运行态:控制步骤指示与按钮禁用
  const [activeStep, setActiveStep] = useState(-1); // 已点亮到第几步(-1=未开始)
  const [err, setErr] = useState<string | null>(null);
  const timerRef = useRef<number | null>(null);

  // 卸载时清掉步骤定时器,避免泄漏。
  useEffect(() => {
    return () => {
      if (timerRef.current != null) window.clearInterval(timerRef.current);
    };
  }, []);

  // 预期模块集(来自 route 阶段派生的静态预期 modulePlan;primary + secondary 的 code)。
  // 【预期,非实际】:仅承载运行前的预期,真实路由在结果页给出。
  const expectedModules = modulePlan
    ? [modulePlan.primary, ...modulePlan.secondary].filter((c) => c && c.trim())
    : [];

  async function run() {
    setRunning(true);
    setErr(null);
    setRunStatus("running");
    setActiveStep(0);

    // 启动确定性步骤指示的伪进度定时器(纯前端逐步点亮,不依赖后端分步返回)。
    // 到倒数第二步就停,末步"留存运行记录"在成功拿到 job_id 后再点亮,避免早于实际完成。
    if (timerRef.current != null) window.clearInterval(timerRef.current);
    timerRef.current = window.setInterval(() => {
      setActiveStep((s) => (s < RUN_STEPS.length - 2 ? s + 1 : s));
    }, STEP_INTERVAL_MS);

    try {
      // 同步一次拿 job_id(createJob 复用现有签名,不改请求)。
      const ref = await createJob(request, mode, enableLlmReport);
      if (timerRef.current != null) {
        window.clearInterval(timerRef.current);
        timerRef.current = null;
      }
      setActiveStep(RUN_STEPS.length - 1); // 点亮末步
      // 成功:落 succeeded 并前进 results(实际 abstain/failed 由结果页回填)。
      setRunStatus("succeeded");
      onRan(ref.job_id);
    } catch (e: unknown) {
      // 失败:停指示、置 failed、显面向用户错误态(不崩,可重试)。
      if (timerRef.current != null) {
        window.clearInterval(timerRef.current);
        timerRef.current = null;
      }
      setRunStatus("failed");
      setErr(e instanceof Error ? e.message : String(e));
      setRunning(false);
      setActiveStep(-1);
    }
  }

  // 最终请求汇总的关键字段(只读展示)。
  const summary: [string, string][] = [
    ["物种", fmt(request.species)],
    ["细胞类型", fmt(request.cell_type)],
    ["扰动类型", fmt(request.perturbation_type)],
    ["扰动对象", fmt(request.perturbation_targets)],
    ["任务类型", fmt(request.task_type)],
  ];

  return (
    <section style={{ maxWidth: "880px" }}>
      {/* 标题区:平实说明(§3.5),不外泄 execution manifest 等内部名词。 */}
      <div style={{ marginBottom: "var(--space-4)" }}>
        <h1
          style={{
            fontFamily: "var(--font-serif)",
            fontSize: "28px",
            fontWeight: 500,
            lineHeight: 1.15,
            letterSpacing: "-0.01em",
            color: "var(--text)",
            margin: 0,
          }}
        >
          运行前确认
        </h1>
        <p
          style={{
            marginTop: "var(--space-3)",
            fontSize: "14px",
            lineHeight: 1.55,
            color: "var(--text-muted)",
            maxWidth: "64ch",
          }}
        >
          下面是即将运行的实验设置。确认无误后开始运行,预测由确定性模型在后端完成,不经语言模型改写。
        </p>
      </div>

      {/* Step 1 · 最终请求汇总(只读) */}
      <Card title="即将运行的实验">
        <table className="kv-table">
          <tbody>
            {summary.map(([k, v]) => (
              <tr key={k}>
                <th>{k}</th>
                <td>{v}</td>
              </tr>
            ))}
          </tbody>
        </table>

        {/* 预期模块(来自上一步的静态预期;标"预期",非实际路由)。 */}
        {expectedModules.length > 0 && (
          <div style={{ marginTop: "var(--space-3)" }}>
            <div
              style={{
                fontSize: "13px",
                color: "var(--text-muted)",
                marginBottom: "var(--space-2)",
                lineHeight: 1.5,
              }}
            >
              预计会用到的模块(仅预期,实际以运行结果为准):
            </div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: "var(--space-2)" }}>
              {expectedModules.map((code) => (
                <span
                  key={code}
                  style={{ display: "inline-flex", alignItems: "center", gap: "6px" }}
                >
                  <code
                    style={{
                      fontFamily: "var(--font-mono)",
                      fontSize: "12.5px",
                      background: "var(--code-bg)",
                      border: "1px solid var(--border)",
                      borderRadius: "var(--radius-sm)",
                      padding: "2px 6px",
                    }}
                  >
                    {code}
                  </code>
                  <Badge tone="neutral">预期</Badge>
                </span>
              ))}
            </div>
          </div>
        )}

        {/* 完整 request(展开细节),mono 字体。 */}
        <details style={{ marginTop: "var(--space-3)" }}>
          <summary
            style={{
              cursor: "pointer",
              fontSize: "13px",
              color: "var(--text-muted)",
            }}
          >
            查看完整运行参数
          </summary>
          <pre className="pretty" style={{ fontFamily: "var(--font-mono)" }}>
            {JSON.stringify(request, null, 2)}
          </pre>
        </details>

        {/* 文字解读开关(§3.5:生成文字解读,可选;不参与预测/治理)。 */}
        <label
          style={{
            display: "flex",
            alignItems: "flex-start",
            gap: "var(--space-2)",
            marginTop: "var(--space-3)",
            fontSize: "13.5px",
            lineHeight: 1.5,
            cursor: running ? "default" : "pointer",
          }}
        >
          <input
            type="checkbox"
            checked={enableLlmReport}
            disabled={running}
            onChange={(e) => setEnableLlmReport(e.target.checked)}
            style={{ marginTop: "2px" }}
          />
          <span>
            生成语言模型改写的叙述(可选)
            <span style={{ color: "var(--text-muted)" }}>
              {" "}
              —— 仅改写措辞方便阅读,不参与预测与可靠性判定。
            </span>
          </span>
        </label>
      </Card>

      {/* Step 2 · 运行进度(确定性步骤指示)。仅在运行开始后显示。 */}
      {activeStep >= 0 && (
        <Card title="运行进度">
          <p
            style={{
              margin: "0 0 var(--space-3)",
              fontSize: "12.5px",
              color: "var(--text-muted)",
              lineHeight: 1.5,
            }}
          >
            以下为标准执行步骤示意,按固定顺序逐步点亮,并非实时逐步流;完整的逐步运行轨迹可在运行结束后的「运行轨迹」中查看。
          </p>
          <ol
            style={{
              listStyle: "none",
              margin: 0,
              padding: 0,
              display: "flex",
              flexDirection: "column",
              gap: "var(--space-2)",
            }}
          >
            {RUN_STEPS.map((label, i) => {
              const done = i < activeStep;
              const current = i === activeStep && running;
              const reached = i <= activeStep;
              return (
                <li
                  key={label}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "var(--space-3)",
                    fontSize: "13.5px",
                    color: reached ? "var(--text)" : "var(--text-muted)",
                    opacity: reached ? 1 : 0.5,
                  }}
                >
                  <span
                    aria-hidden
                    style={{
                      flex: "0 0 auto",
                      width: "18px",
                      height: "18px",
                      borderRadius: "50%",
                      border: `1px solid ${
                        reached ? "var(--accent)" : "var(--border)"
                      }`,
                      background: done
                        ? "var(--accent)"
                        : current
                          ? "color-mix(in srgb, var(--accent) 22%, transparent)"
                          : "transparent",
                      display: "inline-flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontSize: "11px",
                      color: "#fff",
                      lineHeight: 1,
                    }}
                  >
                    {done ? "✓" : ""}
                  </span>
                  <span>
                    {label}
                    {current ? " …" : ""}
                  </span>
                </li>
              );
            })}
          </ol>
        </Card>
      )}

      {/* 失败态:面向用户的错误提示,不崩,可重试(再次点 Start run)。 */}
      {err && (
        <div className="err" style={{ marginTop: "var(--space-4)" }}>
          运行未能完成:{err}
          <div style={{ marginTop: "var(--space-1)", color: "var(--text-muted)" }}>
            可返回上一步检查设置,或再次尝试运行。
          </div>
        </div>
      )}

      {/* 操作行:返回上一步(→route)/ 开始运行。 */}
      <div
        style={{
          display: "flex",
          justifyContent: "flex-end",
          gap: "var(--space-2)",
          marginTop: "var(--space-4)",
        }}
      >
        <Button variant="ghost" onClick={onBack} disabled={running}>
          ← 返回
        </Button>
        <Button onClick={run} disabled={running}>
          {running ? "运行中…" : "开始运行 →"}
        </Button>
      </div>
    </section>
  );
}
