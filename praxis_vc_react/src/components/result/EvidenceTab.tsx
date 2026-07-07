import type { CSSProperties, ReactNode } from "react";
import type { ReportResult } from "../../api";
import Card from "../ui/Card";
import Badge from "../ui/Badge";
import type { BadgeTone } from "../ui/Badge";
import EmptyState from "../ui/EmptyState";
import { EvidenceDistributionChart } from "../visualization";

// Stage 5 · Evidence tab(spec §2 Evidence / §3.5 / Phase9 红线)——把本次运行的证据/审计线索
// 平铺成一张只读证据表:参照规则(rules_referenced)/命中规则(rules_hit)、模型来源(采纳/未采纳/失败)、
// 未通过检查(failed_checks)、审查违规(critic_violations)、注意事项(caution_flags)、证据等级(evidence_level)。
//
// 字段真实位置(读 praxis_virtualcell/agents/report.py + runs/*/report.json 核实,不臆测):
//   - structured_report 顶层:models_used / models_rejected / models_failed(数组)、
//     failed_checks / critic_violations(数组)、caution_flags(【对象】=ortholog_cautions 映射,非数组)、
//     model_disagreement(对象)。
//   - structured_report.provenance 里:rules_referenced / rules_hit(数组)、
//     evidence_level(【对象】:{ level:"E3", rationale:[], ood_signal, aligned_with_disposition })。
//   计划把 rules/evidence_level 描述为在 provenance 下,与真实结构一致;caution_flags/evidence_level
//   实为对象(非计划暗示的裸数组),此处按真实结构容错读取(Array.isArray / typeof / ??)。
//
// 着色语义(§2):有告警/负例的字段用 Badge warn/danger;正常/无违规用 confirmed/neutral。
//   - failed_checks / critic_violations 非空 → danger(硬性未过 / 审查违规)。
//   - models_rejected / models_failed 非空、caution_flags 非空 → warn(需注意,非硬失败)。
//   - models_used / rules_hit 非空 → confirmed(有采纳模型 / 命中规则=有证据支撑)。
//
// 铁律(Phase9 红线):前端只读展示真实字段,不做任何治理裁决、不重算 verdict/等级;
//   offline 为 mock 时如实呈现,不推断真值;配色走 token(组件/Badge 内已守)。

// ── 安全取值助手(structured_report / provenance 是后端 Record,字段可能缺失)──
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

// caution_flags 是 { key: reason } 映射(ortholog_cautions);展平成可读字符串列表。
// 若上游给的是数组(结构演进的兜底),也如实展平。
function cautionList(v: unknown): string[] {
  if (Array.isArray(v)) return v.map((x) => String(x));
  const rec = asRecord(v);
  return Object.entries(rec).map(([k, val]) =>
    val != null && val !== "" ? `${k}:${String(val)}` : k,
  );
}

// ── 小样式(走 token,不硬编码配色)──
const monoStyle: CSSProperties = {
  fontFamily: "var(--font-mono)",
  fontSize: 12,
  background: "var(--code-bg)",
  border: "1px solid var(--border)",
  borderRadius: "var(--radius-sm)",
  padding: "1px 6px",
  color: "var(--text)",
  wordBreak: "break-word",
};
const stackStyle: CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "var(--space-4)",
};
const chipsStyle: CSSProperties = {
  display: "flex",
  flexWrap: "wrap",
  gap: "var(--space-2)",
  alignItems: "center",
};

function Mono({ children }: { children: ReactNode }) {
  return <code style={monoStyle}>{children}</code>;
}

// 证据表一行:名称 / 状态徽标 / 明细(mono chips 或说明文字)。
type EvidenceRow = {
  key: string;
  label: string;
  tone: BadgeTone;
  status: string;
  detail: ReactNode;
};

function EvidenceTable({ rows }: { rows: EvidenceRow[] }) {
  return (
    <div className="table-scroll">
      <table className="kv-table module-table">
        <thead>
          <tr>
            <th style={{ width: "22%" }}>证据项</th>
            <th style={{ width: "18%" }}>状态</th>
            <th>明细</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.key}>
              <td>{r.label}</td>
              <td>
                <Badge tone={r.tone}>{r.status}</Badge>
              </td>
              <td>{r.detail}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// mono chips 明细:字符串列表逐个渲染;空列表给占位破折号。
function Chips({ items, empty = "—" }: { items: string[]; empty?: string }) {
  if (items.length === 0) {
    return <span style={{ color: "var(--text-muted)" }}>{empty}</span>;
  }
  return (
    <span style={chipsStyle}>
      {items.map((it, i) => (
        <Mono key={`${it}-${i}`}>{it}</Mono>
      ))}
    </span>
  );
}

export default function EvidenceTab({ report }: { report: ReportResult }) {
  const sr = report.structured_report ?? {};
  const prov = asRecord(g(sr, "provenance"));

  // 规则(provenance 下)。
  const rulesReferenced = asStrArr(g(prov, "rules_referenced"));
  const rulesHit = asStrArr(g(prov, "rules_hit"));

  // 模型来源(structured_report 顶层)。
  const modelsUsed = asStrArr(g(sr, "models_used"));
  const modelsRejected = asStrArr(g(sr, "models_rejected"));
  const modelsFailed = asStrArr(g(sr, "models_failed"));

  // 治理/边界字段(structured_report 顶层)。
  const failedChecks = asStrArr(g(sr, "failed_checks"));
  const criticViolations = asStrArr(g(sr, "critic_violations"));
  const cautionFlags = cautionList(g(sr, "caution_flags"));

  // 证据等级(provenance 下,是对象:{ level, rationale, ood_signal, aligned_with_disposition })。
  const evLevel = asRecord(g(prov, "evidence_level"));
  const evLevelText = evLevel.level != null ? String(evLevel.level) : "";
  const evRationale = asStrArr(g(evLevel, "rationale"));
  const evOod = evLevel.ood_signal != null ? String(evLevel.ood_signal) : "";

  // 全空判定:无规则、无模型、无治理字段、无证据等级 → EmptyState。
  const allEmpty =
    rulesReferenced.length === 0 &&
    rulesHit.length === 0 &&
    modelsUsed.length === 0 &&
    modelsRejected.length === 0 &&
    modelsFailed.length === 0 &&
    failedChecks.length === 0 &&
    criticViolations.length === 0 &&
    cautionFlags.length === 0 &&
    evLevelText === "";

  if (allEmpty) {
    return (
      <EmptyState
        title="暂无证据明细"
        hint="本次运行未记录可展示的规则、模型来源或审计线索。"
      />
    );
  }

  // 证据分布图入参(与 EvidenceDistributionChart 的入参形态对齐;容错)。
  const dis = asRecord(g(sr, "model_disagreement"));
  const disagreement = {
    score: typeof dis.score === "number" ? dis.score : undefined,
    metric: dis.metric != null ? String(dis.metric) : undefined,
    triggered: typeof dis.triggered === "boolean" ? dis.triggered : undefined,
  };
  const models = { used: modelsUsed, rejected: modelsRejected, failed: modelsFailed };

  // ── 证据表行(着色语义见文件头注释)──
  const rows: EvidenceRow[] = [];

  // 参照规则:纯中性(参照到规则,尚未论及命中)。
  rows.push({
    key: "rules_referenced",
    label: "参照规则",
    tone: "neutral",
    status: rulesReferenced.length > 0 ? `${rulesReferenced.length} 条` : "无",
    detail: <Chips items={rulesReferenced} empty="未参照规则" />,
  });

  // 命中规则:命中=有规则支撑证据 → confirmed;未命中 → neutral。
  rows.push({
    key: "rules_hit",
    label: "命中规则",
    tone: rulesHit.length > 0 ? "confirmed" : "neutral",
    status: rulesHit.length > 0 ? `${rulesHit.length} 条` : "无",
    detail: <Chips items={rulesHit} empty="无规则命中" />,
  });

  // 采纳模型:有采纳 → confirmed;无 → warn(无模型参与需注意)。
  rows.push({
    key: "models_used",
    label: "采纳模型",
    tone: modelsUsed.length > 0 ? "confirmed" : "warn",
    status: modelsUsed.length > 0 ? `${modelsUsed.length} 个` : "无",
    detail: <Chips items={modelsUsed} empty="无采纳模型" />,
  });

  // 未采纳模型:非空 → warn(被治理规则排除,需注意)。
  rows.push({
    key: "models_rejected",
    label: "未采纳模型",
    tone: modelsRejected.length > 0 ? "warn" : "neutral",
    status: modelsRejected.length > 0 ? `${modelsRejected.length} 个` : "无",
    detail: <Chips items={modelsRejected} empty="无未采纳模型" />,
  });

  // 失败模型:非空 → danger(运行失败)。
  rows.push({
    key: "models_failed",
    label: "失败模型",
    tone: modelsFailed.length > 0 ? "danger" : "neutral",
    status: modelsFailed.length > 0 ? `${modelsFailed.length} 个` : "无",
    detail: <Chips items={modelsFailed} empty="无失败模型" />,
  });

  // 未通过检查:非空 → danger(硬性检查未过)。
  rows.push({
    key: "failed_checks",
    label: "未通过检查",
    tone: failedChecks.length > 0 ? "danger" : "confirmed",
    status: failedChecks.length > 0 ? `${failedChecks.length} 项` : "全部通过",
    detail: <Chips items={failedChecks} empty="无未通过检查" />,
  });

  // 审查违规:非空 → danger(critic 判定违规)。
  rows.push({
    key: "critic_violations",
    label: "审查违规",
    tone: criticViolations.length > 0 ? "danger" : "confirmed",
    status: criticViolations.length > 0 ? `${criticViolations.length} 项` : "无违规",
    detail: <Chips items={criticViolations} empty="无审查违规" />,
  });

  // 注意事项(caution_flags,含直系同源等提示):非空 → warn。
  rows.push({
    key: "caution_flags",
    label: "注意事项",
    tone: cautionFlags.length > 0 ? "warn" : "neutral",
    status: cautionFlags.length > 0 ? `${cautionFlags.length} 项` : "无",
    detail: <Chips items={cautionFlags} empty="无额外注意事项" />,
  });

  // 证据等级(evidence_level.level;E1..En 越小越强,前端只如实呈现不解释分级)。
  if (evLevelText !== "" || evRationale.length > 0 || evOod !== "") {
    rows.push({
      key: "evidence_level",
      label: "证据等级",
      tone: "neutral",
      status: evLevelText !== "" ? evLevelText : "—",
      detail:
        evRationale.length > 0 || evOod !== "" ? (
          <span
            style={{
              display: "flex",
              flexDirection: "column",
              gap: "var(--space-1)",
              color: "var(--text-muted)",
              fontSize: 13,
            }}
          >
            {evRationale.length > 0 && <Chips items={evRationale} />}
            {evOod !== "" && (
              <span>
                分布外信号:<Mono>{evOod}</Mono>
              </span>
            )}
          </span>
        ) : (
          <span style={{ color: "var(--text-muted)" }}>—</span>
        ),
    });
  }

  return (
    <div style={stackStyle}>
      {/* 头部引导:说明这是审计视角的证据/来源清单,克制、平实(§3.5)。 */}
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: "var(--space-1)",
          padding: "var(--space-3) var(--space-4)",
          borderRadius: "var(--radius)",
          border: "1px solid var(--border)",
          background: "color-mix(in srgb, var(--primary) 6%, var(--surface))",
        }}
      >
        <strong style={{ fontSize: 14, color: "var(--text)" }}>本次结果的证据与来源</strong>
        <span style={{ fontSize: 13, color: "var(--text-muted)" }}>
          下表汇总本次运行参照/命中的规则、参与的模型,以及未通过的检查与注意事项,供核对。
        </span>
      </div>

      {/* 证据表(全字段;着色语义见行内) */}
      <Card title="证据与审计">
        <EvidenceTable rows={rows} />
      </Card>

      {/* 可选:证据分布图(模型分歧度 + 参与模型分布;组件内自带空态与容错) */}
      <Card title="证据分布">
        <EvidenceDistributionChart disagreement={disagreement} models={models} />
      </Card>
    </div>
  );
}
