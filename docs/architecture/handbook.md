# Cortex Architecture Handbook

## Purpose

Cortex is a production context gate and decision-memory layer for AI-heavy
engineering teams. It ingests Slack, Linear, GitHub, and repo docs, turns raw
source activity into cited engineering context, detects stale or conflicting
decisions, and gives Codex or Claude Code an allow/warn/block signal before
implementation.

This handbook explains the system shape and the reason behind each major
technical choice. ADRs in `docs/architecture/adrs/` are the durable decision
records. The first-principles architecture critique lives in
[`docs/architecture/review.md`](review.md). The implementation-ready v1 entity
and lifecycle spec lives in
[`docs/architecture/v1-entity-state-schema.md`](v1-entity-state-schema.md). The
Kafka message contract lives in
[`docs/architecture/pipeline-event-envelope.md`](pipeline-event-envelope.md).

## Core Product Flow

```text
Codex/Claude Code
  -> local Cortex MCP proxy
  -> hosted Cortex API
  -> retrieval/context gate
  -> evidence pack + allow/warn/block
  -> human approval when blocked
  -> canonical decision saved for future agents
```

The first wow path is:

```text
"I'm implementing Linear issue COR-123. What architecture decisions, diagrams,
Slack threads, PRs, and docs constrain this implementation, and is any context
stale or conflicting?"
```

Cortex should return cited evidence and block when architecture context is
conflicted.

## Target Backend

The new backend is Python-first:

- FastAPI for hosted API, OAuth callbacks, health checks, and admin/debug
  endpoints.
- Pydantic v2 for typed contracts across APIs, workers, and MCP payloads.
- SQLAlchemy + Alembic for Postgres persistence and migrations.
- Async Kafka consumers for ingestion, normalization, chunking, embedding,
  linking, extraction, and indexing workers.
- A local MCP proxy/CLI that authenticates with hosted Cortex by device login.

The old `cortexg` TypeScript code is a reference prototype. Preserve its
concepts, not its implementation language.

## Data Boundary

V1 is hosted-first. Cortex hosts encrypted tenant data and indexes for the first
serious version because it is faster to build, debug, and sell. Customer-managed
or on-prem data planes remain later deployment modes, not the default v1 path.

Cheap but production-shaped infrastructure:

- Postgres for canonical records.
- Kafka-compatible event backbone.
- Object storage for Slack files/images and large raw payloads.
- Qdrant for semantic vectors.
- Postgres full-text search first for lexical retrieval.
- OpenSearch adapter later when lexical scale or filtering demands it.

## Source Pipeline

```text
OAuth connector
  -> backfill jobs
  -> provider webhooks/events
  -> Kafka raw event topics
  -> raw event persistence
  -> normalization workers
  -> source objects + versions
  -> source-aware chunks + OCR text
  -> embedding jobs
  -> lexical/vector indexes
  -> relationship/linking workers
  -> semantic artifact extraction
  -> retrieval/context gate
  -> evidence pack
  -> human-approved canonical memory
```

The raw event log is the rebuildable truth. Derived objects, chunks, embeddings,
relationships, and artifacts must be replayable from raw events plus connector
state.

The dev workbench uses the same pipeline with deterministic fixture providers.
It should make each stage visible with record counts, generated IDs, stage
status, errors, and links to inspect the resulting objects.

## Core Data Contracts

- `OAuthInstallation`: provider install, scopes, token reference, workspace,
  status.
- `SecretRef`: encrypted secret pointer, key version, provider, purpose, status,
  and rotation metadata.
- `SourceConnection`: selected Slack channels, repos, Linear teams/projects, or
  docs roots.
- `WebhookDelivery`: provider delivery ID, signature verification result,
  idempotency key, source connection, and processing status.
- `PipelineRun`: dev/beta diagnostic run that traces seed, ingest, normalize,
  chunk/OCR, embed, index, link, retrieve, gate, and evidence-pack stages.
- `RawEvent`: provider-shaped event payload, external ID, event type, source,
  occurred/received timestamps.
- `ProviderCursor`: backfill/incremental cursor with high/low watermarks.
- `SourceObject`: normalized thread, issue, PR, commit, doc section, file, or
  agent session.
- `SourceFile`: file/image/diagram metadata, object-storage pointer, OCR text,
  provider URL.
- `SourceChunk`: source-aware retrievable unit with content hash and chunking
  version.
- `SemanticArtifact`: extracted decision, implementation constraint, diagram
  reference, risk, open question, owner note, or stale assumption.
- `Relationship`: deterministic or AI-candidate link between source objects,
  chunks, files, issues, PRs, docs, and people.
- `PermissionScope`: v1 source allowlist selection.
- `RetentionPolicy`: workspace/source retention windows for raw payloads, files,
  derived content, and audit metadata.
- `DeletionRequest`: requested deletion scope, status, actor, timestamps, and
  affected stores.
- `DeletionTombstone`: minimal non-content record used for replay safety,
  duplicate prevention, and audit after hard delete.
- `RetrievalRequest`: task/query/issue/repo/file hints and caller context.
- `EvidencePack`: cited retrieved context plus source coverage and exclusions.
- `ContextGateResult`: `allow`, `warn`, or `block` with cited reasons.
- `CanonicalDecision`: human-approved resolution with scope and citations.
- `ApprovalRecord`: approver, action, timestamp, original proposal, final text.
- `ModelInvocation`: provider/model call metadata for embeddings, extraction,
  OCR, reranking, and synthesis.
- `RetrievalEvalCase`: golden query, expected evidence, expected gate, and
  permission expectations.

## Dev Workbench Strategy

Cortex needs an easy visual way to prove the architecture before real connectors
are complete. Add a dev-only workbench that runs deterministic mock data through
the real pipeline interfaces.

The workbench is internal, not the polished customer UI. It is enabled only when
`CORTEX_DEV_WORKBENCH_ENABLED=true` and disabled by default in production.

Workbench route:

```text
GET /dev/workbench
```

Dev endpoints:

- `POST /dev/fixtures/reset`: clear the dev workspace and test indexes.
- `POST /dev/fixtures/seed`: seed fixed Slack, Linear, GitHub, repo docs, and
  file/OCR fixtures.
- `POST /dev/pipeline/run`: run the pipeline end-to-end or by selected stage.
- `GET /dev/pipeline/runs/{run_id}`: inspect timeline, counts, generated record
  IDs, failures, and stage durations.
- `POST /dev/retrieval/query`: run query planning, filters, FTS, Qdrant, merge,
  relationship expansion, evidence building, and context gate.
- `GET /dev/evidence-packs/{id}`: inspect claims, citations, source coverage,
  conflict/staleness signals, and gate result.
- `POST /dev/evals/run`: run golden retrieval evals against the fixture bundle.

The fixture bundle should model the first wow demo:

- Slack thread approving Postgres sessions.
- Slack diagram file with filename/caption/OCR text.
- Linear `COR-123` session migration issue.
- Linear blocker issue for middleware fallback.
- GitHub PR partially migrating session writes.
- Repo doc that still says Redis is source of truth.

Expected result: retrieval returns all five evidence sources and the context
gate returns `block`.

The workbench must not hardcode final UI responses. It should exercise real
service interfaces using deterministic fixture connectors, deterministic
embeddings, and local/object-storage test files.

## Connector Strategy

V1 source order:

1. Slack
2. Linear
3. GitHub
4. Repo docs

Slack is the wedge because architecture decisions and diagrams are often buried
in threads, files, reactions, and links.

Each connector supports:

- OAuth or provider app install.
- Admin-selected source allowlist.
- Backfill.
- Incremental webhook/event ingestion.
- Webhook signature verification.
- Idempotent delivery handling.
- Cursor resume.
- Retry/deadletter handling.
- Provider rate-limit tracking.
- Raw event replay.
- Source health and freshness reporting.

## Kafka Strategy

Kafka is the durable ingestion backbone. Topics should be grouped by pipeline
stage and should carry enough metadata for replay and debugging.

Kafka messages use the shared
[`Pipeline Event Envelope`](pipeline-event-envelope.md). Messages are lightweight
pointers plus routing metadata; raw provider payloads, normalized objects,
chunks, vectors, and evidence packs live in Postgres/object storage/indexes.

Partition key:

```text
{workspace_id}:{source_object_key}
```

Examples:

- Slack thread key: `slack:{team_id}:{channel_id}:{thread_ts || message_ts}`
- Linear issue key: `linear:{workspace_id}:{issue_id}`
- GitHub PR key: `github:{installation_id}:{repo_id}:pr:{number}`
- GitHub commit key: `github:{installation_id}:{repo_id}:commit:{sha}`
- Doc key: `doc:{repo_id}:{path}`

This preserves ordering where it matters while allowing large workspaces to
process many objects in parallel.

## Storage Strategy

Postgres is the system of record for:

- tenants/workspaces,
- OAuth installation metadata and encrypted token references,
- source connections and allowlists,
- raw event metadata,
- source objects/versions,
- chunks,
- source files,
- provider cursors,
- worker/job state,
- semantic artifacts,
- relationships,
- retrieval requests,
- evidence packs,
- canonical decisions,
- approvals,
- webhook deliveries and idempotency keys,
- secret references and OAuth scope grants,
- retention policies, deletion requests, and tombstones,
- rate-limit buckets,
- model invocation logs,
- retrieval eval cases/runs,
- audit records.

Large provider payloads and files go to object storage. Postgres stores hashes,
URLs, object keys, MIME type, size, OCR text, and citation metadata.

## Secrets Strategy

Cortex stores provider tokens and local MCP session secrets through secret
references, not raw application rows. The app database may store metadata such
as provider, workspace, scopes, expiry, rotation status, and encrypted secret
reference. Token material belongs in a managed secrets service or encrypted
secret store with key versioning.

OAuth installs must support:

- expired/revoked states,
- scope drift detection,
- rotation and reauthorization,
- audit records for install, refresh, revoke, and failure.

## Webhook And Idempotency Strategy

Provider webhooks must be verified before they create raw events or Kafka
messages. Cortex stores provider delivery IDs and idempotency keys so retries do
not duplicate source events.

Webhook handling order:

```text
receive provider webhook
  -> verify signature/timestamp
  -> record WebhookDelivery
  -> dedupe by provider delivery/idempotency key
  -> persist raw event metadata
  -> publish Kafka raw event
```

## Retention And Deletion Strategy

Design-partner beta uses configurable retention:

- Default raw events/files retention: 90 days.
- Derived metadata, citations, canonical decisions, approvals, and audit records
  may live longer.
- Workspace/source retention overrides are allowed.

Deletion uses hard delete plus tombstones:

- Delete customer content from Postgres search, Qdrant, object storage, and
  future OpenSearch.
- Retain minimal non-content tombstones for replay safety, idempotency, and
  audit.
- Deleted content must not appear in retrieval, evidence packs, debug output, or
  source coverage details.

## Backpressure And Rate Limits

Connectors and workers must respect provider limits and internal capacity.

Cortex tracks:

- provider rate-limit buckets,
- retry-after times,
- backfill priority,
- cursor progress,
- Kafka consumer lag,
- worker leases/heartbeats,
- failed/deadlettered event counts.

Workers should pause, reschedule, or lower priority rather than repeatedly
calling provider APIs during rate-limit or error windows.

## Retrieval Strategy

Retrieval is hybrid:

- Postgres full-text search for cheap v1 lexical matching.
- Qdrant for vector recall.
- OpenSearch later behind a lexical search adapter.
- Deterministic relationship expansion.
- Optional reranking once evals show need.

Ranking dimensions:

- query relevance,
- source authority,
- recency,
- relationship strength,
- file/issue/repo hints,
- canonical decision priority,
- permission/source allowlist eligibility,
- conflict/staleness signals.

Retrieval must return citations. It should not dump broad memory into the agent.
Chunk sizes, overlap, embedding settings, candidate limits, ranking weights,
gate thresholds, and token budgets are versioned retrieval configuration. See
[`ADR-005 config and tuning`](adrs/005-hybrid-retrieval-stack/config-and-tuning.md).

## Retrieval Evaluation Strategy

Retrieval quality is a product surface. Cortex keeps golden eval cases from day
one.

Metrics:

- Recall@K,
- MRR,
- citation accuracy,
- conflict detection accuracy,
- context gate accuracy,
- permission/source-allowlist safety,
- latency,
- token efficiency.

Benchmark dimensions:

- Postgres full-text only,
- Qdrant only,
- hybrid full-text + Qdrant,
- hybrid + relationship expansion,
- hybrid + reranking,
- Gemini 1536 vs Gemini 3072 vs OpenAI embedding candidates.

## Embedding Strategy

Embeddings are provider-neutral. Gemini is the v1 default, but the schema and
workers must allow OpenAI or another provider without migration pain.

Default:

- Provider: Google Gemini
- Model: `gemini-embedding-2`
- Version: `gemini2-1536-v1`
- Dimensions: `1536`
- Retrieval instructions: document and query prefixes are embedded in input
  text; the deprecated `taskType` request field is not used.

Every embedding record stores provider, model, dimensions, task type,
content hash, vector hash, chunking version, retrieval index version, status,
and error/retry state.

No fine-tuning in v1. Improve quality first with chunking, linking, hybrid
retrieval, reranking, and evals.

## Model Gateway And Cost Strategy

All embedding, extraction, OCR, reranking, and synthesis calls go through a model
gateway. The gateway records provider, model, task type, input size, latency,
estimated cost, retry count, status, and error.

The gateway enables:

- provider neutrality,
- per-workspace budgets,
- model comparisons,
- fallbacks,
- cost dashboards,
- eval reproducibility.

## Chunking Strategy

Chunking is source-aware and versioned.

Carry forward the `cortexg` philosophy:

- Slack: thread-level chunk plus per-message chunks.
- Linear: issue overview plus comments/updates.
- GitHub: PR overview, changed files, reviews/comments, commits.
- Docs: markdown sections.
- Agent sessions: prompt, response, tool, command, file, decision segments.
- Files/diagrams: metadata chunk plus OCR text chunk.

Chunking versions must be explicit so chunks and embeddings can be rebuilt when
strategies change.

## Linking Strategy

Link deterministic evidence first, then AI candidate links.

Deterministic links:

- URLs,
- Linear issue IDs,
- GitHub PR numbers,
- commit SHAs,
- branch names,
- file paths,
- repo names,
- Slack permalinks,
- user identities,
- timestamps.

AI links are lower-trust candidates with confidence, model metadata, and
citations. They can improve recall but should not become canonical decisions
without human approval.

## Permissions V1

Use a simple source allowlist first.

Admins choose:

- Slack channels,
- GitHub repositories,
- Linear teams/projects,
- repo docs roots.

Cortex indexes and retrieves only from allowlisted scopes. Full provider-native
per-user ACL snapshots come later. V1 must still avoid exposing non-allowlisted
source names, snippets, URLs, file names, or debug identifiers.

## Context Gate

Context gate returns:

- `allow`: enough current, non-conflicting context exists.
- `warn`: ambiguity exists, but risk is low enough to proceed.
- `block`: high-impact context is conflicted, stale, missing, or risky.

First blocking categories:

- architecture decision conflicts,
- stale docs versus newer Slack/GitHub/Linear evidence,
- auth/security/permission-sensitive ambiguity,
- missing context for a referenced Linear/GitHub task,
- migrations, billing, infra, deletion, and data-access changes.

Blocked workflows ask the human inside Codex/Claude Code to approve, edit,
proceed with warning, mark unresolved, or stop.

## Canonical Memory

Cortex can propose a canonical decision, but only a human can approve it.

Canonical decisions store:

- final decision text,
- scope,
- citations,
- stale/superseded evidence,
- approver,
- approval action,
- timestamp,
- source request/evidence pack.

Future retrieval prioritizes approved canonical decisions while still showing
historical evidence when it explains conflicts.

## Observability

Production Cortex needs operational visibility from the first real connector:

- OpenTelemetry traces across API, workers, model gateway, retrieval, context
  gate, and dev workbench.
- Structured logs with `trace_id`, `workspace_id`, `source_connection_id`,
  `pipeline_run_id`, `worker_name`, `retrieval_request_id`, and
  `evidence_pack_id`.
- OAuth install status,
- backfill progress,
- webhook lag,
- Kafka consumer lag,
- retry/deadletter counts,
- cursor freshness,
- raw event replay status,
- chunk/index freshness,
- embedding job status,
- Qdrant index freshness,
- evidence pack audit trail,
- blocked/warned/allowed gate counts.

Use Grafana Cloud lean for beta rather than self-hosting Prometheus, Loki, and
Tempo. Start with a small set of critical alerts:

- connector broken or OAuth revoked,
- Kafka lag above threshold,
- worker deadletter spike,
- retrieval error-rate spike,
- model/embedding cost spike,
- Qdrant/index freshness stale,
- webhook signature failure spike.

Initial dashboards:

- Pipeline Health,
- Connector Health,
- Retrieval Quality,
- Embedding/Model Cost,
- Storage/Index Freshness,
- Security/Audit Overview.

The dev workbench is the first operational dashboard. It visualizes the local
fixture pipeline and should later inform the production ops UI.

## Runtime And Deployment Strategy

All Cortex services should run as containers, but Kubernetes is not required for
the beta.

Deployment path:

1. Docker Compose for local development.
2. Simple hosted containers for design-partner beta.
3. Kubernetes when worker isolation, queue-lag autoscaling, or multi-replica
   deployment complexity requires it.

Container boundaries:

- FastAPI API,
- connector/ingestion workers,
- normalization workers,
- chunk/OCR workers,
- embedding/indexing workers,
- retrieval/eval workers,
- local MCP proxy as a separate local process.

Managed infrastructure should handle reverse proxy/load balancing/TLS early
where possible. Add explicit Kubernetes manifests only when the operational need
is proven.

## Layer-Later Platform Components

Some production components are real requirements, but they should enter as
interfaces, config, and documented deployment assumptions before they become
custom infrastructure.

Add now:

- cache interface for ephemeral state,
- rate-limit policy model,
- scheduler/job contract,
- backup/restore runbook shape,
- feature/config flag contract,
- admin action audit model.

Layer later, or include in Phase 0 only when cheap:

- Redis or managed cache for rate-limit counters, short-lived locks, sessions,
  hot health snapshots, and temporary query results. Cache is never source of
  truth.
- Reverse proxy/ingress handled by the hosting platform for TLS, routing,
  request size limits, compression, and basic load balancing. Document the
  contract; do not custom-build it for beta.
- API/user/model-call rate limiting to protect expensive retrieval, embedding,
  model gateway, and connector endpoints.
- Background scheduler for periodic backfills, retention sweeps, deletion jobs,
  health checks, and eval runs. Start with a simple worker cron plus leases;
  move to Temporal only when workflow complexity proves it.
- Backup and restore for Postgres, object storage lifecycle/restore, and
  documented rebuilds of Qdrant/OpenSearch from raw/source truth.
- Feature/config flags for dev workbench access, deterministic versus real
  embeddings, connector rollout, and gradual context-gate blocking.
- Admin/support tools to re-run connector syncs, replay deadletters, force
  re-embed/re-index jobs, and inspect tenant/source health.

## Distributed Coordination Strategy

Do not build custom distributed storage or a custom single-leader control plane
in v1.

Cortex's authority model is:

- Postgres is the transactional source of truth.
- Kafka is the ordered event backbone for pipeline replay.
- Object storage stores large payloads, files, and OCR inputs.
- Qdrant and OpenSearch are derived indexes that can be rebuilt.
- Redis, if present, is ephemeral coordination/cache state only.

Correctness should come from idempotency keys, content hashes, versioned jobs,
worker leases, and replayable events rather than a bespoke leader. For singleton
work such as scheduled retention sweeps or eval runs, use a simple lease:

- Postgres advisory lock or lease row first,
- Redis lock later if Redis already exists,
- Kubernetes CronJob or Temporal only when deployment complexity warrants it.

Kafka consumer groups handle parallel worker ownership for stream processing.
When jobs conflict, workers should safely no-op, retry, or enqueue repair work
instead of relying on one global leader to serialize the system.

## Beta Production Bar

The first production target is design-partner beta, not enterprise compliance.

Build immediately:

- tenant isolation,
- device login/session auth,
- OAuth secret references,
- source allowlists,
- webhook verification/idempotency,
- retention/deletion/tombstones,
- rate-limit/backpressure records,
- deadletters/replay/repair jobs,
- retrieval eval logging,
- audit logs,
- minimal operational metrics.

Layer later:

- full provider-native per-user ACL sync,
- SSO/SAML/SCIM,
- SOC 2 evidence automation,
- customer-managed/on-prem data plane,
- billing and invoice workflows,
- Temporal workflows,
- Redis or managed cache,
- custom rate-limiter service,
- admin/support console beyond minimal debug endpoints,
- advanced feature flag service,
- Kubernetes deployment manifests and autoscaling,
- deep diagram vision beyond metadata and OCR.

## ADR Index

- [ADR-001: Python FastAPI Backend](adrs/001-python-fastapi-backend/)
- [ADR-002: Kafka Event Backbone](adrs/002-kafka-event-backbone/)
- [ADR-003: Hosted-First Data Boundary](adrs/003-hosted-first-data-boundary/)
- [ADR-004: Postgres Source Of Truth](adrs/004-postgres-source-of-truth/)
- [ADR-005: Hybrid Retrieval Stack](adrs/005-hybrid-retrieval-stack/)
- [ADR-006: Provider-Neutral Embeddings](adrs/006-provider-neutral-embeddings/)
- [ADR-007: Source-Aware Chunking](adrs/007-source-aware-chunking/)
- [ADR-008: Deterministic-First Linking](adrs/008-deterministic-first-linking/)
- [ADR-009: Source Allowlist Permissions V1](adrs/009-source-allowlist-permissions-v1/)
- [ADR-010: Local MCP Proxy With Device Login](adrs/010-local-mcp-proxy-device-login/)
- [ADR-011: Slack Files And Diagrams Via Metadata And OCR](adrs/011-slack-files-diagrams-ocr/)
- [ADR-012: Secrets And Token Management](adrs/012-secrets-token-management/)
- [ADR-013: Webhook Security And Idempotency](adrs/013-webhook-security-idempotency/)
- [ADR-014: Retention And Deletion](adrs/014-retention-deletion/)
- [ADR-015: Rate Limits Backpressure And Repair](adrs/015-rate-limits-backpressure-repair/)
- [ADR-016: Retrieval Evals And Model Gateway](adrs/016-retrieval-evals-model-gateway/)
- [ADR-017: Dev Workbench And Deterministic Pipeline Fixtures](adrs/017-dev-workbench-deterministic-fixtures/)
- [ADR-018: Grafana Cloud Lean Observability](adrs/018-grafana-cloud-lean-observability/)
- [ADR-019: Containerized Services Kubernetes Compatible](adrs/019-containerized-services-kubernetes-compatible/)
- [ADR-020: Layered Platform Components](adrs/020-layered-platform-components/)
- [ADR-021: Distributed Coordination Without Custom Leader](adrs/021-distributed-coordination-without-custom-leader/)
