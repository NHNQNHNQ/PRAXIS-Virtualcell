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

// ---- 类型(对应后端 pydantic schema) ----
export interface Health {
  status: string;
  mode: string;
  llm_enabled: boolean;
  runtime_version: string;
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

export interface ProvenanceResult {
  provenance: Record<string, unknown>;
  llm_meta: Record<string, unknown>;
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

// report.md 为纯文本(text/markdown),不走 JSON 解析,单独 fetch。
export async function getReportMarkdown(jobId: string): Promise<string> {
  const res = await fetch(`${API_BASE}/api/reports/${encodeURIComponent(jobId)}/markdown`);
  if (!res.ok) throw new Error(`API ${res.status}: report.md 获取失败`);
  return res.text();
}
