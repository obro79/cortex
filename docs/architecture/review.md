# Cortex Architecture Review

## 1. Executive Summary

Verdict: the architecture is directionally sound.

Cortex is correctly designed as a production context, retrieval, and gating
system rather than a local markdown memory tool. The core choices are strong:
Postgres as source of truth, replayable raw events, provider-neutral source
contracts, hybrid retrieval, cited evidence packs, and human-approved canonical
decisions.

The architecture is slightly complex, but appropriately scoped if the first
implementation stays narrow. The right first build is deterministic fixtures,
Slack wedge ingestion, source objects/chunks, hybrid retrieval, evidence packs,
context gate, and human approval. The wrong first build would be all connectors,
full admin UI, Kubernetes, Temporal, enterprise ACLs, and every platform layer.

Top architectural risks:

1. Retrieval correctness: bad chunking, weak query planning, poor filtering, or
   missing relationships will make the product feel unreliable even if the
   infrastructure is solid.
2. Permission and privacy leakage: source allowlists are acceptable for v1, but
   retrieval, logs, traces, debug endpoints, and source coverage must not expose
   non-allowlisted content or identifiers.
3. Pipeline state complexity: Kafka, workers, embeddings, indexes, replay, and
   deletion are viable only if state machines, retries, idempotency keys, and
   audit trails are explicit from the start.

Top decisions before writing implementation code:

1. Lock the v1 entity/state schema for raw events, source objects, chunks,
   embedding/index jobs, evidence packs, context gate results, approvals, and
   deletion.
2. Lock the retrieval contract: query inputs, filters, ranking dimensions,
   citation shape, source coverage shape, and benchmark acceptance thresholds.
3. Lock the v1 deployment boundary: Docker Compose locally, simple hosted
   containers for beta, managed ingress/TLS, no required Kubernetes, no
   Temporal, and Redis optional only for ephemeral state.

## 2. Product-To-Architecture Mapping

| Product feature | Backend services/modules | Data stored | External APIs/integrations | Async/background jobs | Real-time behavior | V1 simplification |
| --- | --- | --- | --- | --- | --- | --- |
| Slack decision memory | connector service, ingestion service, normalization workers, file/OCR workers, extraction workers | OAuth install, source allowlist, raw events, messages, threads, files, OCR text, chunks, semantic artifacts | Slack OAuth, Slack Events API, Slack Web API | backfill, webhook processing, thread reconstruction, file fetch, OCR, extraction, embedding, indexing | webhook intake and health should be near real time | selected channels only; metadata/OCR for files; no deep diagram vision |
| Linear, GitHub, repo docs context | connector modules, docs importer, normalization workers, relationship builder | issues, comments, PRs, commits, docs, source objects, chunks, relationships | Linear API, GitHub App/API, git/repo docs import | backfills, incremental sync, docs indexing, relationship inference | freshness should be visible, but updates do not need subsecond latency | add after Slack wedge; support fewer object types first |
| Agent retrieval | retrieval service, query planner, permission filter, evidence builder, MCP/API service | retrieval requests, candidate refs, evidence packs, source coverage, permission exclusions | local MCP proxy for Codex/Claude Code | embeddings/indexing prework, retrieval eval runs | agent calls need low latency and compact output | no broad chatbot UI; return structured JSON plus compact cited text |
| Context gate | gate service, conflict detector, risk classifier, canonical memory reader | gate result, risk category, cited reasons, evidence pack ref, audit metadata | MCP tools | offline calibration/evals | must respond during agent workflow | start rule/evidence based; avoid opaque autonomous blocking |
| Human-approved canonical memory | canonical memory service, approval service, audit service | canonical decisions, approval records, superseded evidence refs, scopes | MCP/CLI and later internal UI | re-index approved decisions | approval happens during blocked/warned agent workflow | human approval required; agents can propose but not approve |
| Dev workbench | dev API, fixture providers, pipeline runner, retrieval inspector | fixture data, pipeline runs, generated IDs, eval results | deterministic local/model stubs | seed fixtures, run pipeline stages, run evals | interactive local debugging | internal only; feature-flagged and disabled by default |
| Operations and support | admin endpoints, replay/repair service, observability instrumentation | worker state, cursors, deadletters, audit logs, health snapshots | Grafana Cloud, hosting logs, managed secrets | replay, repair, retention sweep, backup checks, health checks | critical alerts near real time | endpoints before full admin console |

## 3. Proposed System Architecture

### Frontend Architecture

The first frontend is not a customer dashboard. It is an internal dev workbench
that proves the pipeline visually with deterministic data.

Initial surfaces:

- `GET /dev/workbench`: internal pipeline and retrieval workbench.
- Pipeline timeline: seed, ingest, raw event, normalize, chunk/OCR, embed,
  index, link, retrieve, gate.
- Retrieval inspector: query plan, filters, lexical candidates, vector
  candidates, merged ranking, relationship expansion, evidence pack.
- Eval panel: Recall@K, MRR, citation accuracy, conflict detection, gate
  accuracy, latency.

Later minimal UI:

- source health,
- evidence-pack inspector,
- canonical decision history,
- unresolved conflicts,
- connector setup/source selection,
- backfill/replay status.

Do not build a broad chat UI before the agent workflow works.

### Backend Architecture

Use Python/FastAPI as the hosted API and worker runtime.

Core modules:

- API and auth: FastAPI routes, device login, sessions, OAuth callbacks.
- Connectors: Slack first, then Linear, GitHub, repo docs.
- Ingestion: backfills, webhooks, cursors, retries, deadletters.
- Normalization: provider objects into source objects and versions.
- Chunk/OCR: source-aware chunks, file metadata, OCR text.
- Model gateway: embeddings, extraction, OCR, rerank, synthesis.
- Indexing: Postgres full-text, Qdrant vectors, later OpenSearch adapter.
- Relationships: deterministic links first, AI candidate links later.
- Retrieval: query planning, permission filtering, hybrid search, ranking.
- Context gate: allow/warn/block using cited evidence and risk categories.
- Canonical memory: human-approved decisions and supersession.
- Admin/ops: replay, repair, source health, audit, workbench.

### Database And Storage Architecture

Authority model:

- Postgres is the transactional source of truth.
- Kafka is the ordered event backbone for replayable pipeline work.
- Object storage stores large raw payloads, Slack files, images, and OCR inputs.
- Qdrant stores vector indexes and is rebuildable.
- Postgres full-text search is the v1 lexical index.
- OpenSearch is a later adapter for lexical scale and richer filtering.
- Redis, if present, is ephemeral only.

Do not build custom distributed storage or a custom single-leader control plane
in v1. Correctness should come from idempotency keys, content hashes, versioned
jobs, leases, and replayable events.

### Auth And Session Model

Use hosted app auth plus local MCP device login.

Provider tokens must be stored through `SecretRef`, not raw application rows.
The application database stores token metadata only: provider, scopes, expiry,
rotation status, workspace, and secret reference.

Required auth states:

- active,
- expired,
- revoked,
- scope drift,
- reauthorization required.

Every OAuth install, refresh, revoke, failed callback, and scope change must be
audited.

### Background Jobs And Queues

Kafka-compatible topics should be grouped by pipeline stage. Partition by:

```txt
{workspace_id}:{source_object_key}
```

This preserves ordering for a Slack thread, Linear issue, GitHub PR, commit, or
doc path while allowing workspace-level parallelism.

Workers must be idempotent. Jobs should carry source key, content hash,
chunking version, embedding model version, index version, retry count, trace ID,
and workspace ID.

Scheduled jobs start as worker cron plus Postgres advisory lock or lease row.
Temporal and Kubernetes CronJobs are later options when complexity warrants
them.

### External Integrations

V1 order:

1. Slack
2. Linear
3. GitHub
4. Repo docs

Model providers must stay behind a provider-neutral model gateway. Gemini can be
the default embedding provider, but all records must store provider, model,
dimensions, task type, content hash, chunking version, retrieval index version,
status, and retry/error metadata.

### AI And Agent Workflow

Codex or Claude Code calls the local Cortex MCP proxy. The proxy authenticates
with hosted Cortex by device login and calls retrieval/context-gate APIs.

The response must include:

- compact agent-facing text,
- structured JSON,
- cited claims,
- source coverage,
- missing context,
- stale/conflicting evidence,
- permission exclusions,
- gate status: `allow`, `warn`, or `block`.

Agents can propose canonical decisions. Only humans can approve them.

### Observability And Logging

Use OpenTelemetry traces across API, workers, model gateway, retrieval, context
gate, and dev workbench.

Structured logs should include:

- `trace_id`,
- `workspace_id`,
- `source_connection_id`,
- `pipeline_run_id`,
- `worker_name`,
- `retrieval_request_id`,
- `evidence_pack_id`.

Never log OAuth tokens, raw file contents, private URLs, embeddings, non-
allowlisted snippets, or large source payloads.

Use Grafana Cloud lean for beta. Initial dashboards:

- Pipeline Health,
- Connector Health,
- Retrieval Quality,
- Embedding/Model Cost,
- Storage/Index Freshness,
- Security/Audit Overview.

### Admin And Internal Tooling

Start with permission-gated admin endpoints before a full admin console.

Required actions:

- re-run connector sync,
- replay deadletters,
- force re-embed/re-index,
- inspect tenant/source health,
- inspect pipeline run,
- trigger eval run,
- start deletion/retention repair.

Every admin action must create an audit record with actor, resource, action,
trace ID, timestamp, and result.

### Deployment Architecture

Deployment path:

1. Docker Compose for local development.
2. Simple hosted containers for design-partner beta.
3. Kubernetes only when worker isolation, autoscaling, or multi-replica
   deployment complexity proves the need.

Managed infrastructure should handle reverse proxy, TLS, compression, request
size limits, routing, and load balancing early.

## 4. Data Model Review

| Entity | Purpose | Key fields | Relationships | Likely indexes | Lifecycle/state | Retention/privacy |
| --- | --- | --- | --- | --- | --- | --- |
| `Workspace` | Tenant boundary | id, name, status, plan, created_at | has users, installs, sources | id, status | active, suspended, deleting, deleted | root deletion/export boundary |
| `User` | Human actor | id, email, name, status | memberships, approvals, audit logs | email unique | active, disabled | PII; retain audit refs carefully |
| `WorkspaceMembership` | Role in workspace | workspace_id, user_id, role, status | workspace, user | workspace+user unique, role | active, invited, removed | audit role changes |
| `OAuthInstallation` | Provider app install | provider, external_workspace_id, scopes, status, secret_ref_id, expires_at | workspace, secret ref, source connections | workspace+provider, status | installing, active, expired, revoked, scope_drift, reauth_required | no raw token in DB |
| `SecretRef` | Pointer to token material | provider, purpose, key_version, status, external_secret_id | OAuth installs, sessions | provider+purpose, status | active, rotating, revoked | token material outside app DB |
| `SourceConnection` | Selected source allowlist | provider, external_id, source_type, display_name_hash, status | install, raw events, source objects | workspace+provider+external_id, status | active, paused, backfilling, disabled | non-allowlisted sources must not leak |
| `WebhookDelivery` | Webhook dedupe/audit | provider, delivery_id, signature_status, idempotency_key, status | source connection, raw event | provider+delivery_id unique, idempotency_key | received, verified, duplicate, rejected, published, failed | store metadata, not secrets |
| `RawEvent` | Replayable source input | provider, external_event_id, event_type, payload_ref, payload_hash, occurred_at, received_at | source connection, source object | workspace+provider+external_event_id, received_at | persisted, published, replayed, deleted | raw payload retention window |
| `ProviderCursor` | Backfill/incremental progress | connection_id, cursor, high_watermark, low_watermark, status | source connection, backfill job | connection+job_type | active, checkpointed, stale, reset | sensitive provider metadata |
| `BackfillJob` | Historical ingestion job | connection_id, cursor_start, cursor_end, status, attempts | source connection, raw events | workspace+status, connection+status | queued, running, checkpointed, completed, rate_limited, failed_retryable, failed_terminal | audit failures |
| `SourceObject` | Normalized source unit | type, external_id, version, title, url, content_hash, updated_at | source connection, chunks, files, artifacts | workspace+type+external_id, content_hash, updated_at | active, superseded, deleted | content hard-deleted on request |
| `SourceFile` | File/diagram/OCR unit | object_key, mime_type, size, hash, ocr_text, provider_url | source object, chunks | source_object_id, hash | fetched, ocr_pending, ocr_complete, failed, deleted | object storage lifecycle |
| `SourceChunk` | Retrieval unit | source_object_id, chunk_type, text, hash, chunk_version, token_count | source object, embeddings | source_object_id, hash, FTS, chunk_version | active, stale, deleted | no non-allowlisted retrieval |
| `EmbeddingRecord` | Vector provenance | chunk_id, provider, model, dimensions, vector_hash, status, error | source chunk, model invocation | chunk+provider+model+version, status | queued, processing, embedded, failed_retryable, failed_terminal, stale | do not log vectors |
| `IndexJob` | Search/vector index work | target_store, target_id, index_version, status, attempts | chunks, embeddings, workers | workspace+status, target_store+target_id | queued, processing, indexed, failed_retryable, deadlettered | derived and rebuildable |
| `SemanticArtifact` | Extracted decision/risk/etc. | type, text, confidence, citation_refs, extractor_version | source object, chunks, relationships | workspace+type, confidence | candidate, active, superseded, rejected | AI output must be cited |
| `Relationship` | Cross-source link | from_id, to_id, type, method, confidence, evidence_ref | objects, chunks, artifacts | from_id, to_id, type | active, candidate, rejected, stale | AI candidate lower trust |
| `PermissionScope` | V1 retrieval boundary | provider, source_type, external_id, status | workspace, source connection | workspace+provider+external_id | allowed, disabled, deleted | privacy-critical |
| `RetrievalRequest` | Query audit/eval input | query, task_hints, filters, caller, trace_id | evidence pack, gate result | workspace+created_at, caller | received, completed, failed | avoid storing excess prompts |
| `EvidencePack` | Cited retrieval result | claims, citations, coverage, exclusions, token_budget | retrieval request, gate result | request_id, created_at | created, consumed, deleted | no disallowed snippets/IDs |
| `ContextGateResult` | Allow/warn/block decision | status, risk_category, reasons, evidence_pack_id | retrieval request, approvals | workspace+status+created_at | allow, warn, block, resolved | audit all blocks/warnings |
| `CanonicalDecision` | Human-approved memory | text, scope, citations, status, supersedes_id | approvals, evidence pack, artifacts | workspace+scope+status | proposed, needs_review, active, superseded, unresolved | durable but cited |
| `ApprovalRecord` | Human decision audit | actor_id, action, before_text, after_text, timestamp | canonical decision, gate result | decision_id, actor_id | immutable | audit-retained |
| `DeletionRequest` | Privacy deletion workflow | scope, requester, status, affected_stores | tombstones, source objects | workspace+status | requested, validated, deleting, tombstoned, completed, failed | must remove content everywhere |
| `DeletionTombstone` | Non-content replay guard | deleted_resource_type, deleted_resource_hash, deleted_at | deletion request | workspace+resource_hash | active | no source content |
| `ModelInvocation` | Cost/quality trace | task_type, provider, model, input_size, latency, cost, status | embedding/extraction/rerank jobs | workspace+task_type+created_at | completed, failed, retried | no raw prompt/content leakage |
| `AuditLog` | Security/admin trail | actor, action, resource_type, resource_id, trace_id, result | all sensitive actions | workspace+actor+created_at, resource | immutable | retention policy applies |

## 5. State Machines And Critical Flows

### OAuth Installation

```txt
started -> provider_redirect -> callback_received -> active
        -> failed

active -> expired -> reauth_required -> active
active -> revoked
active -> scope_drift -> reauth_required
```

Events: user starts install, provider callback arrives, token exchange succeeds,
token refresh fails, provider revokes token, required scopes change.

Retry behavior: callback/token exchange failures are retryable when provider
error is temporary. Revoked tokens require manual reauthorization.

Manual override: admin can disable install, reauthorize, or remove connection.

Audit: actor, provider, scopes, callback result, token refresh result,
revocation, scope changes.

### Backfill Job

```txt
queued -> running -> checkpointed -> running -> completed
                 -> rate_limited -> scheduled_retry -> running
                 -> failed_retryable -> queued
                 -> failed_terminal -> needs_manual_repair
```

Events: job created, worker lease acquired, page fetched, cursor checkpointed,
provider rate limit hit, provider/API error, max retries exceeded.

Retry behavior: exponential backoff with provider `retry_after` respected.

Manual override: pause, resume, replay from cursor, mark terminal, reset cursor.

Audit: connection, cursor range, pages fetched, events created, failures,
operator actions.

### Webhook Delivery

```txt
received -> signature_verified -> deduped -> raw_event_persisted -> published
        -> rejected_signature
        -> duplicate_ignored
        -> failed_retryable
```

Events: webhook received, signature checked, idempotency key matched, raw event
stored, Kafka publish succeeds/fails.

Retry behavior: publishing failures retry by idempotency key. Signature failures
are terminal.

Manual override: replay verified delivery or inspect rejection metadata.

Audit: provider delivery ID, signature result, idempotency key, trace ID.

### Source Pipeline Processing

```txt
raw_event_published -> normalizing -> normalized -> chunking -> chunked
                    -> embedding -> embedded -> indexing -> indexed
                    -> linking -> linked -> extracting -> artifacts_extracted
                    -> failed_retryable
                    -> deadlettered
```

Events: worker consumes event, content hash changes, chunk version changes,
embedding version changes, index version changes, extraction completes.

Retry behavior: all stages must be idempotent by source object key, content hash,
stage version, and workspace.

Manual override: replay raw event, force re-chunk, force re-embed, force
re-index, replay deadletter.

Audit: stage, worker, trace ID, input/output IDs, counts, duration, errors.

### Embedding And Indexing

```txt
queued -> processing -> completed
       -> provider_rate_limited -> scheduled_retry
       -> failed_retryable -> queued
       -> failed_terminal -> deadlettered
       -> stale -> queued
```

Events: chunk created, model version changes, provider returns vector, provider
rate limit hit, Qdrant/Postgres index write succeeds/fails.

Retry behavior: provider and index transient errors retry; invalid dimensions or
unsupported model config are terminal.

Manual override: force re-embed/re-index by workspace, source, chunk version, or
model version.

Audit: provider, model, dimensions, vector hash, index version, cost, latency,
error.

### Retrieval And Evidence Pack

```txt
request_received -> planned -> candidates_loaded -> permission_filtered
                 -> ranked -> evidence_pack_created
                 -> partial_results
                 -> failed
```

Events: MCP/API request received, filters resolved, lexical search completes,
vector search completes, relationship expansion completes, permission filter
applies, pack is persisted.

Retry behavior: retrieval itself should not hide repeated failures. If one
retriever fails and enough evidence remains, return partial results with source
coverage. If permission filtering fails, fail closed.

Manual override: run eval, inspect query plan, replay request in dev workbench.

Audit: query hints, filters, candidate counts, excluded counts, latency, trace
ID. Do not audit raw private snippets beyond retained evidence pack content.

### Context Gate

```txt
evidence_pack_created -> evaluating -> allow
                                  -> warn
                                  -> block -> human_action_required
                                  -> failed
```

Events: evidence pack created, conflict found, stale source found, missing
required context, risk category matched, human resolves block.

Retry behavior: deterministic gate failures can retry. Permission uncertainty
must fail closed.

Manual override: approve, edit, proceed with warning, mark unresolved, stop.

Audit: gate status, risk category, cited reasons, evidence pack, caller, human
action.

### Canonical Decision

```txt
proposed -> needs_review -> approved -> active
                       -> edited -> approved -> active
                       -> marked_unresolved
                       -> rejected

active -> superseded
```

Events: agent proposes decision, human reviews, human edits/approves/rejects,
newer approved decision supersedes old decision.

Retry behavior: proposal creation may retry; approval actions must be
idempotent and audit-preserving.

Manual override: approve, edit, reject, mark unresolved, supersede.

Audit: original proposal, final text, citations, approver, action, timestamp.

### Deletion And Retention

```txt
requested -> validated -> deleting_postgres -> deleting_object_storage
          -> deleting_vector_search -> deleting_lexical_search -> tombstoned
          -> completed
          -> failed_retryable
          -> failed_terminal -> manual_repair
```

Events: deletion requested, scope validated, content removed from each store,
tombstone written, verification query passes.

Retry behavior: store deletion failures retry. Verification failures stay in
manual repair until fixed.

Manual override: retry store deletion, expand deletion scope, mark repaired only
after verification.

Audit: requester, scope, affected stores, deleted counts, tombstone IDs,
verification result.

## Final Review Notes

Keep the architecture, but enforce the build order. The product will be won or
lost on retrieval accuracy, citation quality, permission safety, and agent
workflow ergonomics. Platform maturity matters, but it should support that core
loop rather than competing with it.

The first implementation should prove:

1. deterministic fixture data flows through the real pipeline interfaces,
2. Slack decisions and diagrams become cited source objects/chunks,
3. hybrid retrieval returns the expected evidence,
4. the context gate blocks on conflict,
5. a human-approved canonical decision changes future retrieval.
