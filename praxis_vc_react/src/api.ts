
export const API_BASE: string =
  (import.meta.env.VITE_API_BASE as string | undefined) ?? "";

export type Mode = "offline" | "llm_assisted";

export interface AskDraft {
  text: string;
  species: string;
  structuredDescription: string;
}

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

export interface ResearchTask {
  schema_version: "vc.research-task.v1";
  task_id: string;
  request: Record<string, unknown>;
  pack_id: string;
  pack_version: string;
  model_name: string;
  model_version: string;
  execution_scope: "research_only";
  scientifically_validated: false;
}

export interface ResearchTaskCompatibility {
  schema_version: "vc.research-task-compatibility.v1";
  task_id: string;
  descriptor_fingerprint: string;
  compatibility_fingerprint: string;
  execution_plan: {
    schema_version: "vc.execution-plan.v2";
    pack_id: string;
    pack_version: string;
    executable: boolean;
    steps: {
      model_name: string;
      model_version: string;
      [key: string]: unknown;
    }[];
    reports: {
      model_name: string;
      model_version: string;
      research_execution_scope?: string;
      scientifically_validated?: boolean;
      [key: string]: unknown;
    }[];
    [key: string]: unknown;
  };
}

export interface JobSummary {
  job_id: string;
  status: string;
  species: string | null;
  perturbation_targets: string[];
  abstain: boolean | null;
  reliability: string | null;
  pack_id: string | null;
  pack_version: string | null;
  pack_fingerprint: string | null;
  execution_scope: "production" | "research_only" | null;
  scientifically_validated: boolean | null;
  models_used: string[];
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

export function getResearchTasks(): Promise<{ tasks: ResearchTask[] }> {
  return req<{ tasks: ResearchTask[] }>("/api/research-tasks");
}

export function getResearchTaskCompatibility(
  taskId: string,
): Promise<ResearchTaskCompatibility> {
  return req<ResearchTaskCompatibility>(
    `/api/research-tasks/${encodeURIComponent(taskId)}/compatibility`,
    { method: "POST" },
  );
}

export function executeResearchTask(
  taskId: string,
  compatibilityFingerprint: string,
): Promise<JobRef> {
  return req<JobRef>(
    `/api/research-tasks/${encodeURIComponent(taskId)}/execute`,
    {
    method: "POST",
    body: JSON.stringify({
        compatibility_fingerprint: compatibilityFingerprint,
    }),
    },
  );
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

export function getModulePlan(jobId: string): Promise<{ module_plan: ModulePlan | Record<string, never> }> {
  return req<{ module_plan: ModulePlan | Record<string, never> }>(
    `/api/reports/${encodeURIComponent(jobId)}/module-plan`);
}

export async function getReportMarkdown(jobId: string): Promise<string> {
  const res = await fetch(`${API_BASE}/api/reports/${encodeURIComponent(jobId)}/markdown`);
  if (!res.ok) throw new Error(`API ${res.status}: Failed to fetch report.md`);
  return res.text();
}


export type Stage = "ask" | "review" | "route" | "run" | "results";

export type RunStatus =
  | "idle"
  | "running"
  | "succeeded"
  | "failed"
  | "abstained";

export interface JobState {
  query: string;
  askDraft: AskDraft | null;
  parsedMode: Mode | null;
  parsedIntent: ParseResult | null;
  reviewDraft: Record<string, unknown> | null;
  confirmedRequest: Record<string, unknown> | null;
  modulePlan: ModulePlan | null;
  runStatus: RunStatus;
  jobId: string | null;
}
