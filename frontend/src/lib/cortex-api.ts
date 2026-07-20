export type Provider = "slack" | "github";
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
  label: string;
  snippet: string;
  citation_url: string;
  source_updated_at: string;
  last_synced_at: string;
  freshness: FreshnessStatus;
  retrieval_paths: string[];
  score_provenance: Record<string, unknown>;
  content_hash: string;
  source_version: string;
};

export type TaskContextPayload = {
  evidence_items: EvidenceItem[];
  source_coverage: { providers_requested: string[]; providers_returned: string[]; evidence_item_count: number };
  freshness: { status: FreshnessStatus; oldest_sync_at?: string; maximum_age_seconds: number };
  conflicts: unknown[];
  missing_context: unknown[];
  retrieval: { status: string; lexical_candidate_count: number; vector_candidate_count: number; partial_reasons: string[] };
  versions: { retrieval_config: string; chunking: string; embedding: string; index: string; ranker: string };
};

export type TaskContextSuccess = {
  contract_version: "cortex.task_context.v1";
  ok: true;
  status: "complete" | "partial" | "no_context";
  request_id: string;
  evidence_pack_id: string;
  trace_id: string;
  live_data: boolean;
  task_context: TaskContextPayload;
  warnings: string[];
};

export type TaskContextFailure = {
  contract_version: "cortex.task_context.v1";
  ok: false;
  status: "denied" | "failed";
  trace_id: string;
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
  return cortexApi<TaskContextResponse>("v1/task-context", {
    method: "POST",
    body: JSON.stringify(request),
  });
}

export type RuntimeHealth = { status: string; checks?: Record<string, string>; issues?: Array<{ field: string; code: string; message: string }> };

export function getRuntimeHealth() {
  return cortexApi<RuntimeHealth>("health/ready");
}
