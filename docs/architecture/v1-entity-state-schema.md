# Cortex V1 Entity And State Schema

## Purpose

This document locks the v1 backend contracts for the core pipeline entities. It
is intentionally implementation-oriented: an engineer should be able to create
Pydantic models, SQLAlchemy tables, migrations, and worker state handling from
this spec without inventing lifecycle states. Kafka messages that move these
entities through the pipeline use
[`docs/architecture/pipeline-event-envelope.md`](pipeline-event-envelope.md).

Shared conventions:

- Every tenant-scoped table has `workspace_id`.
- Every mutable pipeline entity has `created_at`, `updated_at`, and `status`.
- Every worker-owned entity with retries has `attempt_count`, `last_error_code`,
  `last_error_message`, `next_retry_at`, and `last_attempt_at`.
- Content-bearing records store `content_hash` or `payload_hash` when possible.
- Derived records store the version that produced them: chunking version,
  embedding model/version, index version, extractor version, or gate version.
- Customer content must not be written to application logs. Logs use IDs, hashes,
  counts, statuses, and trace IDs.

## Status Enums

Use string enums in the API and database so state remains readable in support
tools.

```txt
RawEventStatus:
  received, persisted, published, processing, processed,
  failed_retryable, deadlettered, deleted

SourceObjectStatus:
  active, superseded, stale, deleted

SourceChunkStatus:
  active, stale, deleted

EmbeddingJobStatus:
  queued, processing, provider_rate_limited, scheduled_retry,
  completed, failed_retryable, failed_terminal, deadlettered, stale

IndexJobStatus:
  queued, processing, completed, failed_retryable,
  failed_terminal, deadlettered, stale

EvidencePackStatus:
  created, consumed, expired, deleted

ContextGateStatus:
  allow, warn, block, failed

ApprovalStatus:
  proposed, needs_review, approved, edited, rejected,
  marked_unresolved, superseded

DeletionRequestStatus:
  requested, validated, deleting, verifying, tombstoned,
  completed, failed_retryable, failed_terminal, manual_repair
```

## Core Entities

### `raw_events`

Purpose: immutable-ish record of provider input used for replay, debugging, and
audit. Raw event payload content may live in object storage when large or
sensitive.

Key fields:

- `id`
- `workspace_id`
- `source_connection_id`
- `provider`: `slack`, `linear`, `github`, `repo_docs`, `fixture`
- `external_event_id`
- `event_type`
- `external_object_key`
- `idempotency_key`
- `payload_ref`
- `payload_hash`
- `payload_size_bytes`
- `occurred_at`
- `received_at`
- `published_at`
- `processed_at`
- `status`
- retry/error fields
- `trace_id`

Relationships:

- belongs to `source_connections`
- may produce one or more `source_objects`
- may be referenced by pipeline runs, deadletters, and deletion requests

Indexes:

- unique `(workspace_id, provider, external_event_id)`
- unique `(workspace_id, idempotency_key)`
- `(workspace_id, source_connection_id, received_at)`
- `(workspace_id, status, next_retry_at)`
- `(workspace_id, external_object_key)`

Lifecycle:

```txt
received -> persisted -> published -> processing -> processed
                         -> failed_retryable -> published
                         -> deadlettered
processed -> deleted
```

Retention/privacy:

- default raw payload/file retention is 90 days for beta unless overridden
- retain non-content metadata and tombstones after hard delete
- do not expose deleted raw event content in replay, workbench, retrieval, or
  debug endpoints

### `source_objects`

Purpose: provider-neutral normalized objects such as Slack threads, Slack
messages, Linear issues, GitHub PRs, commits, docs sections, files, and agent
sessions.

Key fields:

- `id`
- `workspace_id`
- `source_connection_id`
- `provider`
- `object_type`
- `external_object_id`
- `external_object_key`
- `parent_object_id`
- `title`
- `canonical_url`
- `author_external_id`
- `occurred_at`
- `source_updated_at`
- `normalized_version`
- `content_hash`
- `metadata_json`
- `status`
- `superseded_by_id`
- `deleted_at`
- `trace_id`

Relationships:

- belongs to `source_connections`
- produced from one or more `raw_events`
- has many `source_chunks`, `source_files`, `semantic_artifacts`
- participates in `relationships`

Indexes:

- unique `(workspace_id, provider, object_type, external_object_id)`
- `(workspace_id, external_object_key)`
- `(workspace_id, object_type, source_updated_at)`
- `(workspace_id, status)`
- `(workspace_id, content_hash)`

Lifecycle:

```txt
active -> stale -> active
active -> superseded
active -> deleted
superseded -> deleted
```

Retention/privacy:

- source object content must be removed on deletion
- metadata that can identify private sources must not leak when outside the
  source allowlist
- keep only non-content tombstones after deletion

### `source_chunks`

Purpose: retrieval units created from source objects and files.

Key fields:

- `id`
- `workspace_id`
- `source_object_id`
- `source_file_id`
- `chunk_type`: thread, message, issue_overview, comment, pr_overview,
  doc_section, file_metadata, ocr_text, agent_session_segment
- `chunk_index`
- `text`
- `text_hash`
- `token_count`
- `chunking_version`
- `citation_label`
- `citation_url`
- `metadata_json`
- `status`
- `created_from_hash`

Relationships:

- belongs to `source_objects`
- optionally belongs to `source_files`
- has many `embedding_records`
- referenced by retrieval candidates, evidence packs, and semantic artifacts

Indexes:

- `(workspace_id, source_object_id, chunk_index)`
- `(workspace_id, text_hash, chunking_version)`
- Postgres full-text index on `text`
- `(workspace_id, status, chunking_version)`

Lifecycle:

```txt
active -> stale -> deleted
active -> deleted
stale -> active
```

Retention/privacy:

- chunks contain customer content and must be deleted from Postgres full-text
  and vector/search indexes on deletion
- chunk text should not be logged
- chunk IDs for non-allowlisted content must not appear in retrieval output

### `embedding_records`

Purpose: provenance and lifecycle for vector generation. The vector itself lives
in Qdrant; Postgres stores model metadata, hashes, status, and index pointers.

Key fields:

- `id`
- `workspace_id`
- `source_chunk_id`
- `provider`
- `model`
- `dimensions`
- `task_type`
- `embedding_version`
- `chunking_version`
- `input_text_hash`
- `vector_hash`
- `qdrant_collection`
- `qdrant_point_id`
- `status`
- retry/error fields
- `model_invocation_id`

Relationships:

- belongs to `source_chunks`
- belongs to `model_invocations`
- used by `index_jobs`

Indexes:

- unique `(workspace_id, source_chunk_id, provider, model, dimensions,
  embedding_version)`
- `(workspace_id, status, next_retry_at)`
- `(workspace_id, model, dimensions)`
- `(workspace_id, qdrant_collection, qdrant_point_id)`

Lifecycle:

```txt
queued -> processing -> completed
       -> provider_rate_limited -> scheduled_retry -> queued
       -> failed_retryable -> queued
       -> failed_terminal -> deadlettered
completed -> stale -> queued
completed -> deleted
```

Retention/privacy:

- do not log vectors or full embedding inputs
- vectors are derived and must be deleted/rebuilt from chunks
- provider/model metadata is safe for cost and quality dashboards

### `index_jobs`

Purpose: state for writing derived indexes such as Postgres FTS, Qdrant, and
future OpenSearch.

Key fields:

- `id`
- `workspace_id`
- `target_store`: `postgres_fts`, `qdrant`, `opensearch`
- `target_type`: `source_chunk`, `source_object`, `semantic_artifact`,
  `canonical_decision`
- `target_id`
- `operation`: `upsert`, `delete`, `rebuild`
- `index_version`
- `status`
- `attempt_count`
- `next_retry_at`
- `last_error_code`
- `last_error_message`
- `completed_at`
- `trace_id`

Relationships:

- points to indexed target by `target_type`/`target_id`
- may reference `embedding_records` for vector index jobs

Indexes:

- unique `(workspace_id, target_store, target_type, target_id, operation,
  index_version)`
- `(workspace_id, status, next_retry_at)`
- `(workspace_id, target_store, status)`

Lifecycle:

```txt
queued -> processing -> completed
       -> failed_retryable -> queued
       -> failed_terminal -> deadlettered
completed -> stale -> queued
```

Retention/privacy:

- indexes are derived; they must be rebuildable from Postgres/object storage
- delete jobs must remove deleted content from every derived store

### `retrieval_requests`

Purpose: audit and evaluation record for retrieval calls from MCP/API/dev
workbench.

Key fields:

- `id`
- `workspace_id`
- `caller_type`: `mcp`, `api`, `dev_workbench`, `eval`
- `caller_id`
- `query`
- `task_hints_json`
- `filters_json`
- `source_allowlist_snapshot_hash`
- `status`
- `trace_id`
- `started_at`
- `completed_at`
- `latency_ms`

Relationships:

- has one or more `evidence_packs`
- may have one `context_gate_result`

Indexes:

- `(workspace_id, created_at)`
- `(workspace_id, caller_type, created_at)`
- `(workspace_id, status)`
- `(workspace_id, trace_id)`

Lifecycle:

```txt
received -> planned -> completed
        -> partial_results
        -> failed
        -> deleted
```

Retention/privacy:

- task/query text may contain sensitive user input; retain only as long as
  needed for audit/eval
- logs should use request ID and trace ID, not full query text

### `evidence_packs`

Purpose: durable cited context returned to agents and used by context gate and
approvals.

Key fields:

- `id`
- `workspace_id`
- `retrieval_request_id`
- `status`
- `claims_json`
- `citations_json`
- `candidate_summary_json`
- `source_coverage_json`
- `permission_exclusions_json`
- `missing_context_json`
- `stale_context_json`
- `conflict_summary_json`
- `token_budget`
- `ranker_version`
- `created_at`
- `consumed_at`
- `expires_at`

Relationships:

- belongs to `retrieval_requests`
- referenced by `context_gate_results`
- referenced by `canonical_decisions` and `approval_records`

Indexes:

- `(workspace_id, retrieval_request_id)`
- `(workspace_id, status, created_at)`
- `(workspace_id, expires_at)`

Lifecycle:

```txt
created -> consumed
created -> expired
created -> deleted
```

Retention/privacy:

- evidence packs contain source excerpts and citations
- must not include non-allowlisted source names, URLs, file names, snippets, or
  debug IDs
- deletion of source content must delete or redact affected pack content unless
  a retention policy explicitly allows non-content audit metadata

### `context_gate_results`

Purpose: allow/warn/block decision over an evidence pack.

Key fields:

- `id`
- `workspace_id`
- `retrieval_request_id`
- `evidence_pack_id`
- `status`: `allow`, `warn`, `block`, `failed`
- `risk_category`
- `reasons_json`
- `required_actions_json`
- `gate_version`
- `evaluated_at`
- `resolved_at`
- `resolution_action`
- `trace_id`

Relationships:

- belongs to `retrieval_requests`
- belongs to `evidence_packs`
- may have `approval_records`
- may create or reference `canonical_decisions`

Indexes:

- `(workspace_id, status, evaluated_at)`
- `(workspace_id, risk_category, evaluated_at)`
- `(workspace_id, retrieval_request_id)`

Lifecycle:

```txt
evaluating -> allow
           -> warn
           -> block -> resolved
           -> failed
```

Retry/manual behavior:

- retrieval or permission uncertainty should fail closed where possible
- blocked results require human action: approve, edit, proceed with warning,
  mark unresolved, or stop

Retention/privacy:

- gate reasons must cite evidence
- never include hidden source identifiers in reasons or required actions

### `canonical_decisions`

Purpose: human-approved durable memory that future retrieval prioritizes.

Key fields:

- `id`
- `workspace_id`
- `scope_type`
- `scope_ref`
- `title`
- `decision_text`
- `status`
- `evidence_pack_id`
- `supersedes_decision_id`
- `superseded_by_decision_id`
- `created_by_actor_id`
- `approved_by_actor_id`
- `approved_at`
- `source_citations_json`
- `stale_or_superseded_evidence_json`
- `decision_version`

Relationships:

- belongs to `evidence_packs`
- has many `approval_records`
- may supersede another canonical decision
- can be chunked/indexed like a high-authority source object

Indexes:

- `(workspace_id, scope_type, scope_ref, status)`
- `(workspace_id, status, approved_at)`
- `(workspace_id, supersedes_decision_id)`

Lifecycle:

```txt
proposed -> needs_review -> active
         -> rejected
         -> marked_unresolved
active -> superseded
```

Retention/privacy:

- decisions are durable but still customer content
- citations must survive as references, but deleted source content must not be
  reproduced after deletion

### `approval_records`

Purpose: immutable audit trail for human actions on gate results and canonical
decisions.

Key fields:

- `id`
- `workspace_id`
- `actor_id`
- `target_type`: `context_gate_result`, `canonical_decision`
- `target_id`
- `action`: `approve`, `edit`, `proceed_with_warning`, `mark_unresolved`,
  `reject`, `stop`, `supersede`
- `original_text`
- `final_text`
- `rationale`
- `created_at`
- `trace_id`

Relationships:

- belongs to user/membership actor
- belongs to context gate result or canonical decision
- may reference evidence pack

Indexes:

- `(workspace_id, target_type, target_id)`
- `(workspace_id, actor_id, created_at)`
- `(workspace_id, action, created_at)`

Lifecycle:

```txt
created
```

Approval records are immutable. Corrections require a new record.

Retention/privacy:

- may contain customer decision text; protect like source content
- needed for trust and audit, so deletion policy should preserve only
  non-content metadata when content deletion is requested

### `deletion_requests`

Purpose: coordinated hard deletion from Postgres, object storage, Qdrant, future
OpenSearch, evidence packs, and derived indexes.

Key fields:

- `id`
- `workspace_id`
- `requested_by_actor_id`
- `scope_type`: workspace, source_connection, source_object, source_file,
  source_chunk, provider_user
- `scope_ref`
- `reason`
- `status`
- `affected_stores_json`
- `deleted_counts_json`
- `verification_result_json`
- `requested_at`
- `validated_at`
- `completed_at`
- retry/error fields
- `trace_id`

Relationships:

- creates `deletion_tombstones`
- affects raw events, source objects, chunks, files, embeddings, indexes,
  evidence packs, and canonical decisions

Indexes:

- `(workspace_id, status, requested_at)`
- `(workspace_id, scope_type, scope_ref)`
- `(workspace_id, requested_by_actor_id, requested_at)`

Lifecycle:

```txt
requested -> validated -> deleting -> verifying -> tombstoned -> completed
                       -> failed_retryable -> deleting
                       -> failed_terminal -> manual_repair
```

Retry/manual behavior:

- failed store deletes retry
- verification failure requires manual repair
- request cannot be marked completed until retrieval/index verification passes

Retention/privacy:

- deleted customer content must not appear in retrieval, workbench, debug
  output, source coverage, logs, Qdrant, object storage, or OpenSearch
- retain only non-content tombstones for replay safety and audit

### `deletion_tombstones`

Purpose: non-content record proving a deleted source should not be recreated by
replay or webhook retry.

Key fields:

- `id`
- `workspace_id`
- `deletion_request_id`
- `resource_type`
- `resource_hash`
- `provider`
- `external_object_key_hash`
- `deleted_at`
- `retention_expires_at`

Indexes:

- unique `(workspace_id, resource_type, resource_hash)`
- `(workspace_id, provider, external_object_key_hash)`
- `(workspace_id, retention_expires_at)`

Retention/privacy:

- tombstones must not contain original content, titles, URLs, file names, or raw
  external IDs when those values are sensitive

## Critical State Machines

### Raw Event Ingestion

```txt
received -> persisted -> published -> processing -> processed
                         -> failed_retryable -> published
                         -> deadlettered
```

Transition events:

- webhook verified or backfill page fetched
- idempotency key accepted
- raw metadata persisted
- Kafka publish succeeds
- downstream processing succeeds/fails

Audit:

- provider delivery ID, idempotency key, source connection, trace ID, status

### Source Object Rebuild

```txt
raw_event processed -> source_object active
source_object active -> stale -> active
source_object active -> superseded
source_object active -> deleted
```

Transition events:

- new provider version arrives
- normalization version changes
- content hash changes
- deletion request completes

Audit:

- old/new content hash, normalization version, producing raw event IDs

### Embedding And Indexing

```txt
queued -> processing -> completed
       -> provider_rate_limited -> scheduled_retry -> queued
       -> failed_retryable -> queued
       -> failed_terminal -> deadlettered
completed -> stale -> queued
```

Transition events:

- chunk created or changed
- model/index version changes
- provider returns vector
- Qdrant/Postgres/OpenSearch write succeeds/fails

Audit:

- provider, model, dimensions, index version, vector hash, cost, latency

### Evidence And Gate

```txt
retrieval request received -> evidence_pack created -> context_gate allow
                                                   -> context_gate warn
                                                   -> context_gate block
                                                   -> context_gate failed
```

Transition events:

- query planned
- candidates loaded and permission-filtered
- evidence pack persisted
- gate evaluation completes
- human resolves warning/block

Audit:

- request ID, pack ID, gate version, status, risk category, cited reasons

### Approval And Canonical Memory

```txt
proposed -> needs_review -> active
         -> rejected
         -> marked_unresolved
active -> superseded
```

Transition events:

- agent proposes canonical decision
- human approves, edits, rejects, marks unresolved, or supersedes

Audit:

- original text, final text, actor, citations, timestamp, action

### Deletion

```txt
requested -> validated -> deleting -> verifying -> tombstoned -> completed
                       -> failed_retryable -> deleting
                       -> failed_terminal -> manual_repair
```

Transition events:

- deletion requested
- scope validated
- stores deleted
- verification passes/fails
- tombstone written

Audit:

- requester, scope, affected stores, deleted counts, verification result

## V1 Defaults

- Use UUID primary keys.
- Use `jsonb` for provider-specific metadata, source coverage, claims, and
  citations, but keep core states and foreign keys relational.
- Use soft states during processing, hard delete content during deletion.
- Store source text in Postgres only where needed for retrieval and evidence;
  store large payloads/files in object storage.
- Keep Qdrant/OpenSearch rebuildable; never make them source of truth.
- Fail closed on permission ambiguity.
- Require human approval before canonical decisions become active.
