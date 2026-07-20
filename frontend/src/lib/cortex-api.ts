/** The backend accepts connector provider identifiers rather than a closed enum. */
export type Provider = string;
export type TaskContextStatus = "complete" | "partial" | "no_context" | "denied" | "failed";
export type FreshnessStatus = "fresh" | "mixed" | "stale" | "unknown";

export type TaskContextRequest = {
  task: {
    objective: string;
    repository?: string;
    branch?: string;
    issue_ids?: string[];
    pull_request_numbers?: number[];
    file_hints?: string[];
  };
  filters?: { providers?: Provider[]; source_ids?: string[] };
  freshness?: { maximum_age_seconds?: number; require_fresh?: boolean };
  budget?: { maximum_evidence_items?: number; maximum_tokens?: number };
};

export type EvidenceItem = {
  citation_id: string;
  provider: string;
  source_type: string;
  source_object_id: string;
  label: string | null;
  snippet: string;
  citation_url: string | null;
  source_updated_at: string | null;
  last_synced_at: string | null;
  freshness: FreshnessStatus;
  retrieval_paths: string[];
  score_provenance: Record<string, unknown>;
  content_hash: string | null;
  source_version: string | null;
};

export type TaskContextPayload = {
  evidence_items: EvidenceItem[];
  source_coverage: { providers_requested: string[]; providers_returned: string[]; evidence_item_count: number };
  freshness: { status: FreshnessStatus; oldest_sync_at?: string | null; maximum_age_seconds: number };
  conflicts: Array<Record<string, unknown>>;
  missing_context: Array<Record<string, unknown>>;
  retrieval: { status: string; lexical_candidate_count: number; vector_candidate_count: number; partial_reasons: string[] };
  versions: Record<string, string>;
};

export type TaskContextSuccess = {
  contract_version: "cortex.task_context.v1";
  ok: true;
  status: "complete" | "partial" | "no_context";
  request_id: string | null;
  evidence_pack_id: string | null;
  trace_id: string;
  live_data: boolean;
  task_context: TaskContextPayload | null;
  warnings: string[];
  error: null;
};

export type TaskContextFailure = {
  contract_version: "cortex.task_context.v1";
  ok: false;
  status: "denied" | "failed";
  request_id: null;
  evidence_pack_id: null;
  trace_id: string;
  live_data: boolean;
  task_context: null;
  warnings: string[];
  error: { code: string; message: string; retryable: boolean; retry_after_seconds?: number };
};

export type TaskContextResponse = TaskContextSuccess | TaskContextFailure;
export type ApiFailure = { detail?: string };

export async function cortexApi<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/cortex/${path.replace(/^\//, "")}`, {
    ...init,
    headers: { "content-type": "application/json", ...init?.headers },
    cache: "no-store",
  });
  const payload = (await response.json().catch(() => ({}))) as T & ApiFailure;
  if (!response.ok) throw new Error(payload.detail ?? `Request failed (${response.status})`);
  return payload;
}

/** The BFF is the only browser-facing path to the authenticated task-context API. */
export function requestTaskContext(request: TaskContextRequest) {
  return cortexApi<TaskContextResponse>("v1/context/task-context", {
    method: "POST",
    body: JSON.stringify(request),
  });
}

/** The evidence endpoint returns the persisted evidence-pack record, not a task-context DTO. */
export type EvidencePackEnvelope = {
  contract_version: "v1";
  trace_id: string;
  workspace_id: string;
  evidence_pack: Record<string, unknown>;
};

export function getEvidencePack(evidencePackId: string) {
  return cortexApi<EvidencePackEnvelope>(`v1/context/evidence/${encodeURIComponent(evidencePackId)}`);
}

export type RuntimeHealth = { status: string; checks?: Record<string, string>; issues?: Array<{ field: string; code: string; message: string }> };

export function getRuntimeHealth() {
  return cortexApi<RuntimeHealth>("health/ready");
}

export type DemoRunIssue = { code: string; severity: "warning" | "error" };
export type LiveRunCounts = {
  raw_events: number;
  source_objects: number;
  source_chunks: number;
  embeddings_completed: number;
  vector_points_verified: number;
  query_requests: number;
  evidence_packs: number;
  failures: number;
};
export type DemoSourceHealth = {
  source_ref_hash: string;
  provider: string;
  mode: "live" | "imported_snapshot" | "fixture";
  readiness: "ready" | "partial" | "not_ready" | "unavailable";
  freshness: "fresh" | "stale" | "unknown";
  freshness_seconds: number | null;
  counts: LiveRunCounts;
  warnings: DemoRunIssue[];
  errors: DemoRunIssue[];
};
export type DemoRunReport = {
  schema_version: "live-context-run-report/v1";
  mode: "controlled_live_run";
  outcome: "passed" | "failed" | "partial";
  live_data: boolean;
  run_id_hash: string;
  environment: string;
  provider: string;
  source_ref_hash: string;
  collection: string;
  counts: LiveRunCounts;
  freshness_seconds: number | null;
  stages: Record<string, string>;
  disclosure: string;
  next_action: string | null;
};
export type DemoRunReportStatus = {
  contract_version: "cortex.demo_run_report_status.v1";
  trace_id_hash: string;
  available: boolean;
  report: DemoRunReport | null;
  issues: DemoRunIssue[];
};
export type SourceHealthStatus = {
  contract_version: "cortex.source_health.v1";
  trace_id_hash: string;
  available: boolean;
  readiness: "ready" | "partial" | "not_ready" | "unavailable";
  freshness: "fresh" | "stale" | "unknown";
  sources: DemoSourceHealth[];
  issues: DemoRunIssue[];
};

/** Safe aggregate control-plane reads; unavailable is a first-class response. */
export function getDemoRunReport() {
  return cortexApi<DemoRunReportStatus>("v1/demo-runs/latest");
}

export function getSourceHealthStatus() {
  return cortexApi<SourceHealthStatus>("v1/demo-runs/source-health");
}
