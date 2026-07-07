import type { CSSProperties, ReactNode } from "react";
import type { ReportResult } from "../../api";
import Card from "../ui/Card";
import Badge from "../ui/Badge";
import StatusPill from "../ui/StatusPill";
import EmptyState from "../ui/EmptyState";

// Stage 5 · Report tab(spec §2 Report / §3.5)——把 structured_report 拆成证据化分块:
// Summary / Prediction / Reliability decision / Boundary / Narrative 五块 + LLM 边界提示。
// 迁自旧 views/ResultView 的 ReportTab(及 ResultsStage 内联),改用新 ui/Card + Badge + StatusPill,
// 层次靠间距 / 小标题 / 状态点承载,不再依赖旧 App.css 的 .block/.meta 结构类。
//
// 铁律:前端只读展示,不做预测/治理裁决;llm_used_for_prediction 如实显示 +
// 「结果由确定性模型给出,未经语言模型改写」语义(§3.5 已软化文案,沿用不回退)。

// ── 安全取值助手(structured_report 是后端 Record,字段可能缺失)──
function g(obj: Record<string, unknown>, key: string): unknown {
  return obj?.[key];
}
function asArr(v: unknown): unknown[] {
  return Array.isArray(v) ? v : [];
}
function joinArr(v: unknown, sep = ", "): string {
  const arr = asArr(v);
  return arr.length ? arr.map((x) => String(x)).join(sep) : "—";
}
function pretty(v: unknown): string {
  return JSON.stringify(v, null, 2);
}

// ── 小样式(走 token,不硬编码配色)──
const codeStyle: CSSProperties = {
  fontFamily: "var(--font-mono)",
  fontSize: 12,
  background: "var(--code-bg)",
  border: "1px solid var(--border)",
  borderRadius: "var(--radius-sm)",
  padding: "1px 6px",
  color: "var(--text)",
  wordBreak: "break-word",
};
const rowsStyle: CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "var(--space-2)",
};
const rowStyle: CSSProperties = {
  display: "flex",
  gap: "var(--space-3)",
  alignItems: "baseline",
  flexWrap: "wrap",
  fontSize: 13,
  color: "var(--text-muted)",
};
const labelStyle: CSSProperties = { minWidth: 132, color: "var(--text-muted)" };
const stackStyle: CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "var(--space-4)",
};

// 单条 key-value 证据行:左标签、右 mono 值。
function KV({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div style={rowStyle}>
      <span style={labelStyle}>{label}</span>
      <span style={{ color: "var(--text)", flex: 1 }}>{children}</span>
    </div>
  );
}
function Mono({ children }: { children: ReactNode }) {
  return <code style={codeStyle}>{children}</code>;
}

export default function ReportTab({
  report,
  markdown,
}: {
  report: ReportResult;
  markdown?: string;
}) {
  const sr = report.structured_report ?? {};
  const disagreement = (g(sr, "model_disagreement") ?? {}) as Record<string, unknown>;
  const learned = (g(sr, "learned_reliability") ?? {}) as Record<string, unknown>;
  const srProv = (g(sr, "provenance") ?? {}) as Record<string, unknown>;

  const prediction = g(sr, "prediction");
  const abstainFlag = Boolean(g(sr, "abstain"));
  const abstainDecision = String(g(learned, "abstain_decision") ?? "");
  const abstained = abstainFlag || abstainDecision === "abstain";
  const abstainReasons = asArr(g(sr, "abstain_reasons")).map((x) => String(x));
  const downgradeReasons = asArr(g(sr, "downgrade_reasons")).map((x) => String(x));

  // 涉及模块:轻量一行摘要(完整路由图归 ModuleRoutingTab / Task 9.20,不在此重复)。
  const primaryModule = String(g(sr, "primary_module") ?? "");

  return (
    <div style={stackStyle}>
      {/* §3.5:结果由确定性模型给出,未经语言模型改写;llm_used_for_prediction 如实显示。 */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "var(--space-2)",
          fontSize: 13,
          color: "var(--text-muted)",
        }}
      >
        <Badge tone="confirmed">
          结果由确定性模型给出,未经语言模型改写
        </Badge>
        <span>
          llm_used_for_prediction:<Mono>{String(report.llm_used_for_prediction)}</Mono>
        </span>
      </div>

      {/* abstain 突出:置顶醒目条,给出 abstain 原因 */}
      {abstained && (
        <div
          style={{
            padding: "var(--space-3) var(--space-4)",
            borderRadius: "var(--radius)",
            border: "1px solid color-mix(in srgb, var(--danger) 30%, transparent)",
            background: "color-mix(in srgb, var(--danger) 8%, var(--surface))",
            color: "var(--danger)",
            display: "flex",
            flexDirection: "column",
            gap: "var(--space-2)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
            <Badge tone="danger">已 abstain</Badge>
            <strong style={{ fontSize: 14 }}>本次未给出预测结论</strong>
          </div>
          {abstainReasons.length > 0 ? (
            <ul style={{ margin: 0, paddingLeft: "var(--space-5)", fontSize: 13 }}>
              {abstainReasons.map((r, i) => (
                <li key={i}>{r}</li>
              ))}
            </ul>
          ) : (
            <span style={{ fontSize: 13 }}>未记录具体原因。</span>
          )}
        </div>
      )}

      {/* 块 1:Summary */}
      <Card title="概要">
        <div style={rowsStyle}>
          <KV label="request_id">
            <Mono>{String(g(sr, "request_id") ?? "—")}</Mono>
          </KV>
          <KV label="使用的模型">
            <Mono>{joinArr(g(sr, "models_used"))}</Mono>
          </KV>
          <KV label="被拒绝的模型">
            <Mono>{joinArr(g(sr, "models_rejected"))}</Mono>
          </KV>
          <KV label="失败的模型">
            <Mono>{joinArr(g(sr, "models_failed"))}</Mono>
          </KV>
          {primaryModule && (
            <KV label="涉及模块">
              <Mono>{primaryModule}</Mono>
              <span style={{ marginLeft: "var(--space-2)", color: "var(--text-muted)" }}>
                （完整路由见「模块路由」）
              </span>
            </KV>
          )}
        </div>
      </Card>

      {/* 块 2:Prediction */}
      <Card
        title="预测"
        actions={
          abstained ? (
            <Badge tone="danger">已 abstain</Badge>
          ) : (
            <Badge tone="confirmed">已给出预测</Badge>
          )
        }
      >
        {abstained ? (
          <p style={{ color: "var(--text-muted)", fontSize: 13, margin: 0 }}>
            本次已 abstain,无预测结论（原因见上方提示）。
          </p>
        ) : (
          <pre className="json">{pretty(prediction)}</pre>
        )}
        <div style={{ ...rowStyle, marginTop: "var(--space-3)" }}>
          <span style={labelStyle}>模型间分歧</span>
          <span style={{ color: "var(--text)" }}>
            score=<Mono>{String(g(disagreement, "score") ?? "—")}</Mono>
            {" · "}metric=<Mono>{String(g(disagreement, "metric") ?? "—")}</Mono>
            {" · "}triggered=<Mono>{String(g(disagreement, "triggered") ?? "—")}</Mono>
          </span>
        </div>
      </Card>

      {/* 块 3:Reliability decision */}
      <Card title="可靠性判定">
        <div style={rowsStyle}>
          <KV label="reliability">
            <Mono>{String(g(sr, "reliability") ?? "—")}</Mono>
          </KV>
          <KV label="mode">
            <Mono>{String(g(learned, "reliability_mode") ?? "—")}</Mono>
          </KV>
          <KV label="reliability_score">
            <Mono>{String(g(learned, "reliability_score") ?? "—")}</Mono>
          </KV>
          <KV label="abstain_decision">
            <Mono>{abstainDecision || "—"}</Mono>
          </KV>
          <KV label="model_version">
            <Mono>{String(g(learned, "model_version") ?? "—")}</Mono>
          </KV>
          <KV label="artifact_sha256">
            <code style={{ ...codeStyle, fontSize: 10 }}>
              {String(g(learned, "artifact_sha256") ?? "—")}
            </code>
          </KV>
        </div>
        {downgradeReasons.length > 0 && (
          <div className="warn" style={{ marginTop: "var(--space-3)" }}>
            降级原因:{downgradeReasons.join("；")}
          </div>
        )}
      </Card>

      {/* 块 4:Boundary */}
      <Card title="边界与规则">
        <div style={rowsStyle}>
          <KV label="failed_checks">
            <Mono>{joinArr(g(sr, "failed_checks"))}</Mono>
          </KV>
          <KV label="critic_violations">
            <Mono>{joinArr(g(sr, "critic_violations"))}</Mono>
          </KV>
          <KV label="caution_flags">
            <code style={codeStyle}>{pretty(g(sr, "caution_flags"))}</code>
          </KV>
          <KV label="rules_referenced">
            <Mono>{joinArr(g(srProv, "rules_referenced"), "；")}</Mono>
          </KV>
          <KV label="rules_hit">
            <Mono>{joinArr(g(srProv, "rules_hit"), "；")}</Mono>
          </KV>
        </div>
      </Card>

      {/* 块 5:Narrative(自然语言解读)——narrative 缺失自然降级 */}
      <Card
        title="文字解读"
        actions={
          report.narrative_report ? <StatusPill status="confirmed" /> : undefined
        }
      >
        {report.narrative_report ? (
          <>
            <div className="note">
              由结构化结果生成，语言模型未改动预测/治理结论。
            </div>
            <pre className="narrative">{report.narrative_report}</pre>
          </>
        ) : markdown ? (
          <pre className="narrative">{markdown}</pre>
        ) : (
          <EmptyState
            title="未生成文字解读"
            hint="可在运行前确认时勾选“生成文字解读（可选）”。"
          />
        )}
      </Card>
    </div>
  );
}
