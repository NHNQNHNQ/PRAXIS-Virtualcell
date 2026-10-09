import type { CSSProperties, ReactNode } from "react";
import type { ProvenanceResult } from "../../api";
import Card from "../ui/Card";
import Button from "../ui/Button";
import EmptyState from "../ui/EmptyState";
import Skeleton from "../ui/Skeleton";

// Stage 5 · Provenance tab(spec §2 Provenance / §3.5 / §4 ⑥ Provenance summary card)——
// 把本次运行的溯源/审计线索,从「裸 pre JSON」升级为分区审计页:job 标识、消息规模、参照/命中规则、
// 模型来源、审查违规、证据等级、涉及模块、待学习项;末尾保留完整 provenance JSON(--font-mono)供逐字核对;
// 提供「下载 provenance JSON」与「复制溯源摘要」两个纯前端动作。
//
// 字段真实位置(读 runs/*/provenance.json + praxis_vc_api/main.py 的 /provenance 端点核实,不臆测):
//   getProvenance 返回 { provenance, llm_meta }。provenance 顶层真实字段:
//     n_messages(number)、rules_referenced / rules_hit(string[])、ortholog_cautions(对象映射)、
//     rejection_reasons(对象映射)、models_used / models_rejected / models_failed(string[])、
//     critic_violations(string[])、module_plan(对象:species/primary/secondary/overall_verdict/entries)、
//     evidence_level(对象:{ level, rationale[], ood_signal, aligned_with_disposition })、
//     learning_queue(对象:{ items[], notes[] })。
//   spec §2 罗列的 timestamp / model versions / report hash 等并不在 /provenance 载荷内
//   (它们在 report.json 的 learned_reliability 下,本 tab 只拿到 prov+jobId),故此处只呈现 provenance
//   实有字段 + jobId,缺失字段一律容错(?? / typeof / Array.isArray),绝不臆造。
//
// 文案(§3.5):provenance 属审计区,面向要审计的科学家,精确术语(rules_hit / evidence_level /
//   critic_violations 等)可保留,但分区标题与引导用平实中文承载,整体克制,不写系统日志/AI 营销腔。
//
// 降级:
//   · prov 为 null(未到 / 加载中)→ Skeleton,不崩;
//   · prov 非空但无任何可展示字段 → EmptyState 兜底,不崩。
//
// 铁律(Phase9 红线):前端只读展示真实字段,不做任何治理裁决、不重算等级 / verdict;
//   下载 / 复制均为纯前端本地操作(Blob / clipboard),不上传任何数据;配色走 token,不硬编码。

// ── 安全取值助手(provenance 是后端 Record,字段可能缺失 / 结构演进)──
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
function asArr(v: unknown): unknown[] {
  return Array.isArray(v) ? v : [];
}

// 对象映射(ortholog_cautions / rejection_reasons)展平成 "key:reason" 可读列表;空映射 → []。
function mapList(v: unknown): string[] {
  const rec = asRecord(v);
  return Object.entries(rec).map(([k, val]) =>
    val != null && val !== "" ? `${k}:${String(val)}` : k,
  );
}

function pretty(v: unknown): string {
  return JSON.stringify(v, null, 2);
}

// 前端下载:把内容存为本地文件(纯前端,不上传任何数据)。迁自 ResultsStage / 旧 ResultView 工具条逻辑。
function download(filename: string, content: string, mime: string) {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

// 复制到剪贴板(纯前端)。失败静默(权限 / 非安全上下文),不阻断展示。
function copy(text: string) {
  void navigator.clipboard?.writeText(text).catch(() => {});
}

// ── 小样式(走 token,不硬编码配色)──
const stackStyle: CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "var(--space-4)",
};
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
const chipsStyle: CSSProperties = {
  display: "flex",
  flexWrap: "wrap",
  gap: "var(--space-2)",
  alignItems: "center",
};
// 完整 JSON 区:等宽、可横向滚动、不撑破页面宽度。
const jsonPreStyle: CSSProperties = {
  margin: 0,
  fontFamily: "var(--font-mono)",
  fontSize: 12,
  lineHeight: 1.5,
  color: "var(--text)",
  background: "var(--code-bg)",
  border: "1px solid var(--border)",
  borderRadius: "var(--radius-sm)",
  padding: "var(--space-3)",
  maxHeight: 420,
  overflow: "auto",
  whiteSpace: "pre",
};

function Mono({ children }: { children: ReactNode }) {
  return <code style={monoStyle}>{children}</code>;
}

// 审计一行:名称 / 值(mono chips 或说明文字)。
type AuditRow = {
  key: string;
  label: string;
  detail: ReactNode;
};

function AuditTable({ rows }: { rows: AuditRow[] }) {
  return (
    <div className="table-scroll">
      <table className="kv-table module-table">
        <thead>
          <tr>
            <th style={{ width: "28%" }}>审计项</th>
            <th>内容</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.key}>
              <td>{r.label}</td>
              <td>{r.detail}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// mono chips 明细:字符串列表逐个渲染;空列表给占位文字。
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

export default function ProvenanceTab({
  prov,
  jobId,
}: {
  prov: ProvenanceResult | null;
  jobId: string;
}) {
  // 加载中 / 未到达:骨架占位,不崩。
  if (prov == null) {
    return (
      <Card title="溯源">
        <Skeleton lines={6} />
      </Card>
    );
  }

  const p = asRecord(prov.provenance);
  const llmMeta = asRecord(prov.llm_meta);

  // ── provenance 真实字段(缺失容错)──
  const nMessages = typeof g(p, "n_messages") === "number" ? Number(g(p, "n_messages")) : null;
  const rulesReferenced = asStrArr(g(p, "rules_referenced"));
  const rulesHit = asStrArr(g(p, "rules_hit"));
  const orthologCautions = mapList(g(p, "ortholog_cautions"));
  const rejectionReasons = mapList(g(p, "rejection_reasons"));
  const modelsUsed = asStrArr(g(p, "models_used"));
  const modelsRejected = asStrArr(g(p, "models_rejected"));
  const modelsFailed = asStrArr(g(p, "models_failed"));
  const criticViolations = asStrArr(g(p, "critic_violations"));

  // direct-v2 provenance: execution contract + immutable plan/compatibility report.
  const executionContract =
    g(p, "execution_contract") != null ? String(g(p, "execution_contract")) : "";
  const executionPlan = asRecord(g(p, "execution_plan"));
  const directSteps = Array.isArray(g(executionPlan, "steps"))
    ? (g(executionPlan, "steps") as unknown[]).map(asRecord)
    : [];
  const compatibilityReports = Array.isArray(g(p, "compatibility_reports"))
    ? (g(p, "compatibility_reports") as unknown[]).map(asRecord)
    : [];
  const directReport = compatibilityReports[0] ?? asRecord(asArr(g(executionPlan, "reports"))[0]);
  const directModels = directSteps.map((step) => {
    const name = String(g(step, "model_name") ?? "—");
    const version = String(g(step, "model_version") ?? "—");
    return `${name}@${version}`;
  });
  const directScope = String(g(directReport, "research_execution_scope") ?? "—");

  // module_plan(对象):primary / secondary / overall_verdict / entries。
  const modulePlan = asRecord(g(p, "module_plan"));
  const mpPrimary = modulePlan.primary != null ? String(modulePlan.primary) : "";
  const mpSecondary = asStrArr(g(modulePlan, "secondary"));
  const mpVerdict = modulePlan.overall_verdict != null ? String(modulePlan.overall_verdict) : "";
  const mpEntries = Array.isArray(modulePlan.entries) ? modulePlan.entries.length : 0;

  // evidence_level(对象):{ level, rationale[], ood_signal, aligned_with_disposition }。
  const evLevel = asRecord(g(p, "evidence_level"));
  const evLevelText = evLevel.level != null ? String(evLevel.level) : "";
  const evRationale = asStrArr(g(evLevel, "rationale"));
  const evOod = evLevel.ood_signal != null ? String(evLevel.ood_signal) : "";

  // learning_queue(对象):{ items[], notes[] }。只呈现规模,不展开细节(细节在完整 JSON 里)。
  const learningQueue = asRecord(g(p, "learning_queue"));
  const lqItems = Array.isArray(learningQueue.items) ? learningQueue.items.length : 0;

  // 全空判定:provenance 无任何可展示字段(极端历史 job / 空 provenance)→ EmptyState。
  const hasModulePlan = mpPrimary !== "" || mpVerdict !== "" || mpEntries > 0;
  const allEmpty =
    nMessages == null &&
    rulesReferenced.length === 0 &&
    rulesHit.length === 0 &&
    orthologCautions.length === 0 &&
    rejectionReasons.length === 0 &&
    modelsUsed.length === 0 &&
    modelsRejected.length === 0 &&
    modelsFailed.length === 0 &&
    criticViolations.length === 0 &&
    !hasModulePlan &&
    evLevelText === "" &&
    evRationale.length === 0 &&
    evOod === "" &&
    lqItems === 0 &&
    executionContract === "";

  // 溯源摘要文本(供 copy;含 provenance + llm_meta,与旧工具条一致)。
  const provSummary = pretty({ provenance: prov.provenance, llm_meta: prov.llm_meta });

  // 下载 / 复制工具条(纯前端本地操作)。
  const actions = (
    <>
      <Button
        variant="ghost"
        size="sm"
        onClick={() =>
          download(`${jobId}_provenance.json`, pretty(prov.provenance), "application/json")
        }
      >
        下载 provenance JSON
      </Button>
      <Button variant="ghost" size="sm" onClick={() => copy(provSummary)}>
        复制溯源摘要
      </Button>
    </>
  );

  if (allEmpty) {
    return (
      <Card title="溯源" actions={actions}>
        <EmptyState
          title="暂无溯源信息"
          hint="本次运行未记录可展示的规则、模型来源或审计线索;完整载荷仍可在下方 JSON 中核对。"
        />
        <div style={{ marginTop: "var(--space-4)" }}>
          <div style={{ fontSize: 13, color: "var(--text-muted)", marginBottom: "var(--space-2)" }}>
            完整 provenance JSON
          </div>
          <pre style={jsonPreStyle}>{pretty(prov.provenance)}</pre>
        </div>
      </Card>
    );
  }

  // ── 审计分区行 ──
  // 标识区:job 标识 + 消息规模。
  const idRows: AuditRow[] = [
    { key: "job_id", label: "job 标识", detail: <Mono>{jobId}</Mono> },
  ];

  const directRows: AuditRow[] = [];
  if (executionContract !== "") {
    directRows.push(
      {
        key: "execution_contract",
        label: "执行合同",
        detail: <Mono>{executionContract}</Mono>,
      },
      {
        key: "execution_plan",
        label: "执行计划",
        detail: (
          <span style={chipsStyle}>
            <Mono>{String(g(executionPlan, "schema_version") ?? "—")}</Mono>
            <Mono>{String(g(executionPlan, "plan_id") ?? "—")}</Mono>
          </span>
        ),
      },
      {
        key: "pack",
        label: "组学 Pack",
        detail: (
          <Mono>
            {String(g(executionPlan, "pack_id") ?? "—")}@
            {String(g(executionPlan, "pack_version") ?? "—")}
          </Mono>
        ),
      },
      {
        key: "direct_models",
        label: "执行模型",
        detail: <Chips items={directModels} empty="无执行模型" />,
      },
      {
        key: "research_scope",
        label: "研究执行边界",
        detail: (
          <span style={chipsStyle}>
            <Mono>{directScope}</Mono>
            <Mono>
              research_authorized=
              {String(g(directReport, "research_execution_authorized") ?? "—")}
            </Mono>
          </span>
        ),
      },
      {
        key: "science_policy",
        label: "科学 / 生产状态",
        detail: (
          <span style={chipsStyle}>
            <Mono>
              scientifically_validated=
              {String(g(directReport, "scientifically_validated") ?? "—")}
            </Mono>
            <Mono>
              benchmark_passed={String(g(directReport, "benchmark_passed") ?? "—")}
            </Mono>
            <Mono>
              production_promoted={String(g(directReport, "production_promoted") ?? "—")}
            </Mono>
          </span>
        ),
      },
    );
  }
  if (nMessages != null) {
    idRows.push({
      key: "n_messages",
      label: "消息步数",
      detail: <Mono>{nMessages}</Mono>,
    });
  }

  // 规则区:参照规则 / 命中规则。
  const ruleRows: AuditRow[] = [
    {
      key: "rules_referenced",
      label: "参照规则",
      detail: <Chips items={rulesReferenced} empty="未参照规则" />,
    },
    {
      key: "rules_hit",
      label: "命中规则",
      detail: <Chips items={rulesHit} empty="无规则命中" />,
    },
  ];

  // 模型区:采纳 / 未采纳 / 失败 + 未采纳缘由 + 直系同源提示。
  const modelRows: AuditRow[] = [
    {
      key: "models_used",
      label: "采纳模型",
      detail: <Chips items={modelsUsed} empty="无采纳模型" />,
    },
    {
      key: "models_rejected",
      label: "未采纳模型",
      detail: <Chips items={modelsRejected} empty="无未采纳模型" />,
    },
    {
      key: "models_failed",
      label: "失败模型",
      detail: <Chips items={modelsFailed} empty="无失败模型" />,
    },
  ];
  if (rejectionReasons.length > 0) {
    modelRows.push({
      key: "rejection_reasons",
      label: "未采纳缘由",
      detail: <Chips items={rejectionReasons} />,
    });
  }
  if (orthologCautions.length > 0) {
    modelRows.push({
      key: "ortholog_cautions",
      label: "直系同源提示",
      detail: <Chips items={orthologCautions} />,
    });
  }

  // 治理 / 证据区:审查违规 + 证据等级。
  const govRows: AuditRow[] = [
    {
      key: "critic_violations",
      label: "审查违规",
      detail: <Chips items={criticViolations} empty="无审查违规" />,
    },
  ];
  if (evLevelText !== "" || evRationale.length > 0 || evOod !== "") {
    govRows.push({
      key: "evidence_level",
      label: "证据等级",
      detail: (
        <span
          style={{
            display: "flex",
            flexDirection: "column",
            gap: "var(--space-1)",
            color: "var(--text-muted)",
            fontSize: 13,
          }}
        >
          <span>
            等级:<Mono>{evLevelText !== "" ? evLevelText : "—"}</Mono>
            {evOod !== "" && (
              <>
                {"  "}分布外信号:<Mono>{evOod}</Mono>
              </>
            )}
          </span>
          {evRationale.length > 0 && <Chips items={evRationale} />}
        </span>
      ),
    });
  }

  // 模块 / 学习区:涉及模块概览 + 待学习项规模。
  const moduleRows: AuditRow[] = [];
  if (hasModulePlan) {
    moduleRows.push({
      key: "module_plan",
      label: "涉及模块",
      detail: (
        <span style={{ display: "flex", flexDirection: "column", gap: "var(--space-1)" }}>
          <span>
            主模块:<Mono>{mpPrimary !== "" ? mpPrimary : "—"}</Mono>
            {"  "}综合结论:<Mono>{mpVerdict !== "" ? mpVerdict : "—"}</Mono>
          </span>
          <span style={{ color: "var(--text-muted)", fontSize: 13 }}>
            辅助模块:<Chips items={mpSecondary} empty="无" />
            {"  "}模块条目:{mpEntries} 条
          </span>
        </span>
      ),
    });
  }
  if (lqItems > 0) {
    moduleRows.push({
      key: "learning_queue",
      label: "待学习项",
      detail: <span style={{ color: "var(--text-muted)" }}>{lqItems} 项(明细见完整 JSON)</span>,
    });
  }

  return (
    <Card title="溯源" actions={actions}>
      <div style={stackStyle}>
        {/* 头部引导:说明这是审计视角的溯源清单,克制、平实(§3.5)。 */}
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
          <strong style={{ fontSize: 14, color: "var(--text)" }}>本次运行的溯源与审计记录</strong>
          <span style={{ fontSize: 13, color: "var(--text-muted)" }}>
            下方分区汇总本次运行的标识、参照/命中的规则、模型来源、审查与证据等级、涉及模块,供审计核对;完整载荷见末尾 JSON,可下载或复制摘要留档。
          </span>
        </div>

        {/* 标识 */}
        <Card title="运行标识">
          <AuditTable rows={idRows} />
        </Card>

        {directRows.length > 0 && (
          <Card title="Direct-v2 执行边界">
            <AuditTable rows={directRows} />
          </Card>
        )}

        {/* 规则 */}
        <Card title="规则来源">
          <AuditTable rows={ruleRows} />
        </Card>

        {/* 模型 */}
        <Card title="模型来源">
          <AuditTable rows={modelRows} />
        </Card>

        {/* 治理 / 证据 */}
        <Card title="审查与证据等级">
          <AuditTable rows={govRows} />
        </Card>

        {/* 模块 / 学习(仅在有内容时渲染,避免空区) */}
        {moduleRows.length > 0 && (
          <Card title="涉及模块与待学习项">
            <AuditTable rows={moduleRows} />
          </Card>
        )}

        {/* 完整 provenance JSON(逐字核对) */}
        <Card title="完整 provenance JSON">
          <div style={{ fontSize: 13, color: "var(--text-muted)", marginBottom: "var(--space-2)" }}>
            以下为本次运行的完整溯源载荷,供逐字核对;可用上方按钮下载或复制摘要。
          </div>
          <pre style={jsonPreStyle}>{pretty(prov.provenance)}</pre>
          {Object.keys(llmMeta).length > 0 && (
            <>
              <div
                style={{
                  fontSize: 13,
                  color: "var(--text-muted)",
                  margin: "var(--space-3) 0 var(--space-2)",
                }}
              >
                语言模型元数据(llm_meta)
              </div>
              <pre style={jsonPreStyle}>{pretty(prov.llm_meta)}</pre>
            </>
          )}
        </Card>
      </div>
    </Card>
  );
}
