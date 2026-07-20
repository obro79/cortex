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
