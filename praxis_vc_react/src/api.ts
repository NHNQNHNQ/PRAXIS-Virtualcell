// PRAXIS-VirtualCell 前端 API client。
// 铁律:前端只展示,绝不在此做预测/治理判断;默认 offline;不存/不显示 API key。
// 所有科学决策均由后端确定性 runtime 完成,本文件仅做 HTTP 调用与类型定义。

// 默认同源(相对路径 ""):FastAPI serve 同源托管 dist 时,前端请求当前 origin 的 /api/*,
// 无需 CORS、不硬编码 IP —— 部署到任意主机(如 10.102.106.53)开箱即用。
// dev(Vite 5173)经 vite.config.ts 的 proxy 把 /api 转发到后端;
// 需指向异地后端时设 VITE_API_BASE 覆盖。
export const API_BASE: string =
  (import.meta.env.VITE_API_BASE as string | undefined) ?? "";

export type Mode = "offline" | "llm_assisted";

export interface AskDraft {
  text: string;
  species: string;
  structuredDescription: string;
}

// ---- 类型(对应后端 pydantic schema) ----
export interface Health {
  status: string;
  mode: string;
  llm_enabled: boolean;
  product_version: string;
  api_protocol_version: string;
  runtime_protocol_version: string;
  runtime_version: string;
  git_sha: string;
}

export interface ParseResult {
  candidate_request: Record<string, unknown>;
  schema_valid: boolean;
  missing_fields: string[];
  errors: string[];
  clarification_required: boolean;
  parser: string;
  llm_used: boolean;
  fallback_used: boolean;
  assumptions: string[];
  llm_metadata: Record<string, unknown>;
}

export interface JobRef {
  job_id: string;
  status: string;
}

export interface JobSummary {
  job_id: string;
  status: string;
  species: string | null;
  perturbation_targets: string[];
  abstain: boolean | null;
  reliability: string | null;
}

export interface ReportResult {
  structured_report: Record<string, unknown>;
  narrative_report: string | null;
  trace_url: string;
  provenance_url: string;
  markdown_url: string;
  llm_used_for_prediction: boolean;
}

export type TraceStep = Record<string, unknown>;

export interface TraceResult {
  trace: TraceStep[];
}

export interface ExecutionPackIdentity {
  pack_id: string;
  pack_version: string;
  fingerprint: string;
}

export interface ExecutionModelIdentity {
  name: string;
  version: string;
  fingerprint: string;
  compatibility_fingerprint: string;
  executable: boolean;
}

export interface ExecutionIdentity {
  schema_version?: string;
  legacy_adapter?: boolean;
  pack?: ExecutionPackIdentity | null;
  models?: ExecutionModelIdentity[];
  fingerprint?: string;
  [key: string]: unknown;
}

export interface ProvenanceResult {
  provenance: Record<string, unknown>;
  llm_meta: Record<string, unknown>;
  execution_identity: ExecutionIdentity;
}

export interface CellPreset {
  id: string;
  species: string;
  cell_type: string;
  label: string;
  example_perturbation_type?: string;
  example_targets?: string[];
  modules?: string[];
}

export interface Options {
  species: string[];
  perturbation_type: string[];
  task_type: string[];
  cell_type_examples: string[];
  cell_type_free_text: boolean;
  cell_presets: CellPreset[];
}

export interface ModuleInfo {
  id: string;
  code: string;
  display_name: string;
  engines: string[];
  pillars: string[];
}

export interface ModulePlanEntry {
  module: string;
  display_name: string;
  role: string;
  engine: string;
  route_disposition: string;
  species_support: string;
  species_verdict: string;
  verdict: string;
  mismatch: string | null;
  caution_flags: string[];
  data_gated: boolean;
  pillars: string[];
  reason: string;
  available_models: string[];
}

export interface ModulePlan {
  species: string;
  primary: string;
  secondary: string[];
  overall_verdict: string;
  entries: ModulePlanEntry[];
  notes: string[];
}

export interface DataSpecies {
  id: string;
  taxon_id: string;
  scientific_name: string;
}

export interface DataCatalogFile {
  id: string;
  filename: string;
  media_type: string;
  size_bytes: number;
  sha256: string;
  source_url: string;
  available: boolean;
  download_url: string;
}

export interface DataCatalogDataset {
  id: string;
  version: string;
  title: string;
  species: {
    runtime_id: string;
    taxon_id: string;
    scientific_name: string;
  };
  modality: string;
  value_semantics: string;
  observations: number;
  features: number;
  source: {
    landing_page: string;
    citation: string;
  };
  terms: {
    id: string;
    name: string;
    url: string;
  };
  usage_status: "download_only";
  scientifically_validated: false;
  files: DataCatalogFile[];
}

export interface DataCatalog {
  schema_version: "vc.data-catalog.v1";
  species: DataSpecies[];
  datasets: DataCatalogDataset[];
  upload: {
    enabled: boolean;
    quarantine_only: true;
    max_file_bytes: number;
    total_quota_bytes: number;
    accepted_extensions: string[];
  };
}

export interface UploadReceipt {
  schema_version: "vc.upload-receipt.v1";
  upload_id: string;
  status: "quarantined";
  species: string;
  filename: string;
  size_bytes: number;
  sha256: string;
  declared_content_type: string | null;
  created_at: string;
}

export interface PackRecord {
  schema_version: "vc.pack-record.v1";
  pack_id: string;
  pack_version: string;
  pack_fingerprint: string;
  manifest_schema_version: string | null;
  taxon: {
    ontology_id: string;
    scientific_name: string;
  } | null;
  assembly: {
    name: string;
    accession: string;
  } | null;
  modalities: {
    name: string;
    ontology_id: string;
  }[];
  feature_namespaces: {
    name: string;
    version: string;
    id_format: string;
  }[];
  asset_count: number | null;
  source: "builtin" | "registered";
  validation_status: "valid" | "invalid" | "unchecked";
  pack_valid: boolean | null;
  model_compatible: boolean | null;
  scientifically_validated: false;
  reasons: string[];
}

export interface ModelCapability {
  name: string;
  version: string;
  fingerprint: string;
  status: string;
  species: string[];
  taxon: string[];
  modalities: {
    name: string;
    ontology_id: string;
  }[];
  cell_domain: Record<string, unknown>;
  task: string;
  outputs: string[];
  feature_namespaces: {
    name: string;
    version: string;
    id_format: string;
  }[];
  scientifically_validated: false;
}

export interface PackCatalog {
  schema_version: "vc.pack-catalog.v1";
  packs: PackRecord[];
  model_capabilities: ModelCapability[];
  scientifically_validated: false;
}

export interface PackFactoryCatalog {
  schema_version: "vc.pack-factory-catalog.v1";
  configured: boolean;
  receipts: {
    receipt_fingerprint: string;
    status: "quarantined";
    pack_valid: boolean | null;
    factory_registered: boolean;
    model_compatible: null;
    executable: false;
  }[];
  reviews: {
    review_fingerprint: string;
    candidate_fingerprint: string;
    decision: "approve_for_strict_validation" | "reject";
  }[];
  validations: {
    validation_report_fingerprint: string;
    candidate_fingerprint: string;
    pack_valid: boolean;
    registration_allowed: boolean;
    passed: boolean;
  }[];
  decisions: {
    operator_decision_fingerprint: string;
    candidate_fingerprint: string;
    decision: "approve_register" | "reject";
  }[];
  candidates: {
    candidate_fingerprint: string;
    status: "candidate_unvalidated";
    reviewed: boolean;
    validation_passed: boolean;
    factory_registered: boolean;
    pack_valid: boolean | null;
    model_compatible: null;
    executable: false;
    scientifically_validated: false;
    production_promoted: false;
  }[];
  registrations: {
    registration_fingerprint: string;
    factory_registered: true;
    pack_valid: true;
    model_compatible: null;
    executable: false;
    scientifically_validated: false;
    production_promoted: false;
    superseded_by: string | null;
  }[];
  supersessions: Record<string, unknown>[];
  review_count: number;
  validation_count: number;
  operator_decision_count: number;
  registration_count: number;
  supersession_count: number;
  write_api_enabled: false;
}

// ---- 内部 fetch 助手 ----
async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    let detail = "";
    try {
      const body = await res.json();
      detail = (body as { detail?: string }).detail ?? JSON.stringify(body);
    } catch {
      detail = res.statusText;
    }
    throw new Error(`API ${res.status}: ${detail}`);
  }
  return (await res.json()) as T;
}

// ---- 公开方法 ----
export function health(): Promise<Health> {
  return req<Health>("/api/health");
}

export function parse(text: string, mode: Mode): Promise<ParseResult> {
  return req<ParseResult>("/api/parse", {
    method: "POST",
    body: JSON.stringify({ text, mode }),
  });
}

export function createJob(
  request: Record<string, unknown>,
  mode: Mode,
  enable_llm_report: boolean,
): Promise<JobRef> {
  return req<JobRef>("/api/jobs", {
    method: "POST",
    body: JSON.stringify({ request, mode, enable_llm_report }),
  });
}

export function listJobs(): Promise<{ jobs: JobSummary[] }> {
  return req<{ jobs: JobSummary[] }>("/api/jobs");
}

export function getReport(jobId: string): Promise<ReportResult> {
  return req<ReportResult>(`/api/reports/${encodeURIComponent(jobId)}`);
}

export function getTrace(jobId: string): Promise<TraceResult> {
  return req<TraceResult>(`/api/reports/${encodeURIComponent(jobId)}/trace`);
}

export function getProvenance(jobId: string): Promise<ProvenanceResult> {
  return req<ProvenanceResult>(`/api/reports/${encodeURIComponent(jobId)}/provenance`);
}

// 只读枚举 + cell 预设(供前端下拉)。权威仍在后端,前端只展示。
export function getOptions(): Promise<Options> {
  return req<Options>("/api/options");
}

export function getModules(): Promise<{ modules: ModuleInfo[] }> {
  return req<{ modules: ModuleInfo[] }>("/api/modules");
}

export function getDataCatalog(species?: string): Promise<DataCatalog> {
  const query = species ? `?species=${encodeURIComponent(species)}` : "";
  return req<DataCatalog>(`/api/data-catalog${query}`);
}

export function getPackCatalog(): Promise<PackCatalog> {
  return req<PackCatalog>("/api/packs");
}

export function getPackFactoryCatalog(): Promise<PackFactoryCatalog> {
  return req<PackFactoryCatalog>("/api/pack-factory");
}

export async function uploadData(
  species: string,
  file: File,
  token: string,
): Promise<UploadReceipt> {
  const body = new FormData();
  body.append("species", species);
  body.append("file", file, file.name);
  const res = await fetch(`${API_BASE}/api/data-uploads`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const payload = (await res.json()) as { detail?: string };
      detail = payload.detail ?? detail;
    } catch {
      // Keep the HTTP status text when an upstream proxy did not return JSON.
    }
    throw new Error(`API ${res.status}: ${detail}`);
  }
  return (await res.json()) as UploadReceipt;
}

// 该 job 的实际模块路由结果(只读)。不可路由 job 返回空 module_plan。
export function getModulePlan(jobId: string): Promise<{ module_plan: ModulePlan | Record<string, never> }> {
  return req<{ module_plan: ModulePlan | Record<string, never> }>(
    `/api/reports/${encodeURIComponent(jobId)}/module-plan`);
}

// report.md 为纯文本(text/markdown),不走 JSON 解析,单独 fetch。
export async function getReportMarkdown(jobId: string): Promise<string> {
  const res = await fetch(`${API_BASE}/api/reports/${encodeURIComponent(jobId)}/markdown`);
  if (!res.ok) throw new Error(`API ${res.status}: report.md 获取失败`);
  return res.text();
}

// ---- UI 派生类型(spec §6 状态机;仅前端使用,不对应任何新端点/请求) ----
// Phase 9 P2:7 步扁平流程 → 5 阶段状态机。以下三类型只服务前端状态管理,
// 不改上面任何请求方法,不新增后端调用。

// 5 阶段:Ask→Review→Route→Run→Results(旧 7 步映射见计划状态机映射表)。
export type Stage = "ask" | "review" | "route" | "run" | "results";

// 运行状态机:idle=未运行;running=同步执行中(确定性步骤指示,非流式);
// succeeded/failed/abstained=终态(实际 abstain/failed 由结果页回填)。
export type RunStatus =
  | "idle"
  | "running"
  | "succeeded"
  | "failed"
  | "abstained";

// 集中式作业状态:回退只改 stage 不清以下字段,故回退不丢数据。
export interface JobState {
  query: string; // Ask 阶段自然语言输入
  askDraft: AskDraft | null; // Ask 的三个表单字段,回退时按原结构恢复
  parsedMode: Mode | null; // 最近一次 /api/parse 使用的模式
  parsedIntent: ParseResult | null; // /api/parse 结果(复用现有 ParseResult)
  reviewDraft: Record<string, unknown> | null; // Review 尚未确认的编辑,供回退后恢复
  confirmedRequest: Record<string, unknown> | null; // Review 阶段编辑组装的 request
  modulePlan: ModulePlan | null; // Route 静态预期(前端派生)/ Results 实际(/module-plan)
  runStatus: RunStatus;
  jobId: string | null; // createJob 产出
}
