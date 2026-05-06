# Cortex Implementation Roadmap

## Build Principle

Cortex should be built as a production connector and context-gating system from the start, while keeping the first demo narrow. The architecture must support OAuth connectors, backfills, event-driven updates, replay, permissions, scalable retrieval, and agent-native approval.

Do not build a local markdown-memory toy first and hope to productionize it later. Build the production-shaped spine early, then fill in source depth incrementally.

The locked architecture choices and tradeoffs live in
[`docs/architecture/handbook.md`](architecture/handbook.md) and its ADRs. The
v1 entity fields, indexes, and lifecycle states live in
[`docs/architecture/v1-entity-state-schema.md`](architecture/v1-entity-state-schema.md).

## Target Architecture

```text
Python FastAPI API + local MCP proxy
  -> OAuth connector
  -> backfill jobs
  -> provider webhooks/events
  -> Kafka raw event topics
  -> Postgres raw event metadata + object storage payloads/files
  -> async Python normalization workers
  -> source objects
  -> source-aware chunks + OCR
  -> semantic extraction
  -> relationship graph
  -> Postgres full-text + Qdrant indexes
  -> source allowlist permissions
  -> retrieval and context gate
  -> evidence pack
  -> human-approved canonical memory
```

## Core Services

- Connector service: OAuth installs, tokens, scopes, source selection.
- Ingestion service: backfills, webhook intake, retries, cursors.
- Event log: Kafka append-only pipeline with Postgres raw-event metadata for replay and audit.
- Normalization workers: provider events into canonical source objects.
- Extraction workers: decisions, diagrams, constraints, risks, open questions.
- Relationship builder: links Slack, Linear, GitHub, docs, files, people, issues.
- Indexer: Postgres full-text and Qdrant vector indexes; OpenSearch adapter later.
- Permission service: v1 source allowlists, later provider-native ACL snapshots.
- Retrieval service: cited evidence packs.
- Context gate service: allow/warn/block decisions for agent workflows.
- Canonical memory service: human-approved resolutions and durable decisions.
- MCP/API service: Codex/Claude Code integration.
- Observability surface: lag, failures, freshness, coverage, permission exclusions.

## Data Contracts

Create these contracts before deep implementation:

- `OAuthInstallation`
- `SourceConnection`
- `RawEvent`
- `BackfillJob`
- `WebhookEvent`
- `ProviderCursor`
- `SourceObject`
- `SourceFile`
- `SourceChunk`
- `SemanticArtifact`
- `Relationship`
- `PermissionSnapshot`
- `PermissionScope`
- `RetrievalRequest`
- `EvidencePack`
- `ContextGateResult`
- `CanonicalDecision`
- `ApprovalRecord`

These should be provider-neutral. Slack, Linear, GitHub, and repo docs should plug into the same pipeline.

## Phase 0: Production Skeleton

Goal: create the production-shaped repo without overbuilding every service.

Deliverables:

- Python package with lint, typecheck, test, build.
- FastAPI app shell.
- Pydantic v2 contract models.
- SQLAlchemy/Alembic migration shell.
- Containerized API and worker entrypoints for Docker Compose/local development.
- Core contract files.
- SQLAlchemy/Pydantic models matching `docs/architecture/v1-entity-state-schema.md`.
- Storage interface.
- Worker interface.
- Kafka event abstraction.
- Pipeline event envelope matching `docs/architecture/pipeline-event-envelope.md`.
- OpenTelemetry instrumentation hooks and trace context contract.
- Cache interface for ephemeral state, with a no-op/in-memory local default.
- Rate-limit policy contract for provider, API, user, and model-call limits.
- Scheduler/job contract for backfills, retention sweeps, deletion jobs, health checks, and eval runs.
- Feature/config flag contract for dev workbench, embedding provider mode, connector rollout, and context-gate rollout.
- Backup/restore runbook skeleton for Postgres, object storage, and derived indexes.
- MCP server shell.
- CLI shell.
- Minimal test fixture framework.
- Dev-only `/dev/workbench` visual pipeline harness guarded by `CORTEX_DEV_WORKBENCH_ENABLED`.
- Deterministic Slack, Linear, GitHub, repo docs, and diagram/OCR fixture bundle.
- Architecture docs for connector, ingestion, permissions, and context gate.

Validation:

- Typecheck.
- Unit tests for contracts and tool schemas.
- CLI smoke test.
- MCP handler smoke test.
- Docker Compose smoke test for API plus one worker role.
- Dev guard test for `/dev/*` endpoints.
- Fixture seed and pipeline-run smoke test.
- Cache, rate-limit, scheduler, and feature-flag contracts have local defaults and do not require Redis, Temporal, or Kubernetes.

## Phase 1: Slack Wedge Connector

Goal: make Slack the first high-value source because engineering decisions and diagrams are buried there.

Deliverables:

- Slack OAuth install flow.
- Workspace/team/channel selection.
- Backfill selected channels.
- Slack Events API intake for messages, edits, deletes, files, links, and thread replies.
- Raw Slack event persistence.
- Kafka publication keyed by workspace and Slack thread/message object.
- Cursor and retry model.
- Thread reconstruction.
- File/link metadata extraction.
- Source coverage for freshness and ingestion lag.

Validation:

- Backfill fixture test.
- Webhook fixture test.
- Replay raw events into source objects.
- Cursor resume test.
- Failed event retry/deadletter test.

## Phase 2: Slack Decision And Diagram Extraction

Goal: turn Slack from raw messages into useful engineering context.

Deliverables:

- Source objects for messages, threads, files, diagrams, links.
- Source files with object-storage pointers, MIME type, filename, Slack permalink, thread/message references, and OCR text.
- Semantic artifacts:
  - decision,
  - implementation constraint,
  - diagram reference,
  - risk,
  - open question,
  - owner note,
  - stale assumption.
- Basic classifier/extractor interface.
- Citation links back to Slack permalink, thread, file, and timestamp.
- Confidence scoring.

Validation:

- Golden Slack thread fixtures.
- Extraction tests for decisions, diagrams, constraints, and open questions.
- Citation integrity tests.
- No unsupported source shape breaks the pipeline.

## Phase 3: Linear + GitHub + Repo Docs

Goal: connect task intent and implementation evidence to Slack decisions.

Deliverables:

- Linear OAuth or API key connector.
- Linear issues, comments, projects, labels, statuses, assignees.
- GitHub App/OAuth connector.
- GitHub issues, PRs, reviews, comments, commits, changed files.
- Repo docs importer for markdown, diagrams, ADRs, and architecture docs.
- Relationship builder:
  - Linear issue to GitHub PR,
  - Slack thread to Linear issue,
  - Slack thread to GitHub PR,
  - docs to code paths,
  - diagrams to source files/components.

Validation:

- Provider fixture tests.
- Relationship inference tests.
- End-to-end retrieval across Slack, Linear, GitHub, and docs.
- Source coverage reports missing or stale providers without crashing retrieval.

## Phase 4: Retrieval And Evidence Packs

Goal: return task-specific, cited context instead of broad memory dumps.

Deliverables:

- `retrieve_context` MCP tool.
- `get_related_work` MCP tool.
- Hybrid lexical/vector retrieval interface.
- Postgres full-text search for v1 lexical retrieval.
- Qdrant vector search with provider-neutral embeddings.
- Ranking by relevance, recency, source authority, relationship strength, and permission.
- Evidence pack format:
  - claims,
  - citations,
  - source coverage,
  - related objects,
  - missing context,
  - stale context,
  - permission exclusions.
- Compact text output for agents plus structured JSON.

Validation:

- Golden demo query test.
- Ranking tests.
- Max-token budget tests.
- Evidence citations always resolve to source objects.

## Phase 5: Context Gate

Goal: Cortex can warn or block agent implementation when high-impact context is unsafe.

First gate categories:

- architecture decision conflicts,
- stale docs versus newer source evidence,
- auth/security/permission-sensitive ambiguity,
- missing task context,
- migrations, billing, infra, deletion, data access.

Deliverables:

- `check_context_gate` MCP tool.
- `ContextGateResult` statuses: `allow`, `warn`, `block`.
- Conflict detection across decisions and sources.
- Evidence ranking for conflicting claims.
- Risk classifier from task, issue, file paths, and source context.
- Agent-facing block message with required human actions.

Validation:

- Conflict fixtures return `block`.
- Low-risk ambiguity returns `warn`.
- Clear, current evidence returns `allow`.
- Gate output is compact and cited.

## Phase 6: Human-Approved Canonical Memory

Goal: agent proposes, human approves, Cortex remembers.

Deliverables:

- `propose_canonical_decision` MCP tool.
- `approve_canonical_decision` MCP tool.
- Approval actions:
  - approve,
  - edit,
  - proceed with warning,
  - mark unresolved,
  - stop.
- Canonical decision persistence with approver, timestamp, scope, citations, and superseded evidence.
- Retrieval prioritizes canonical decisions while preserving cited historical context.

Validation:

- Approved decision appears in future retrieval.
- Edited decision preserves approval metadata.
- Superseded/stale evidence is visible but ranked lower.
- Agent cannot silently create canonical decisions without approval.

## Phase 7: Permissions And Security

Goal: make production team usage credible.

Deliverables:

- OAuth scope model.
- Token encryption/secrets boundary.
- Source allowlists for Slack channels, GitHub repos, Linear teams/projects, and docs roots.
- Retrieval only from allowlisted sources.
- Debug output audit.
- Later-ready user identity mapping across Slack, Linear, GitHub.
- Later-ready channel/repo/project permission snapshot model.

Validation:

- Non-allowlisted content does not leak title, URL, external ID, excerpt, chunk ID, source object ID, source name, or file name.
- Allowlisted content remains retrievable.
- Source coverage can safely report excluded counts.
- Security review before real customer data.

## Phase 8: Observability And Operations

Goal: operators can trust freshness and recover from failures.

Deliverables:

- OpenTelemetry traces across API, workers, model gateway, retrieval, context gate, and dev workbench.
- Structured logs with `trace_id`, `workspace_id`, `source_connection_id`, `pipeline_run_id`, `worker_name`, `retrieval_request_id`, and `evidence_pack_id`.
- Grafana Cloud lean dashboards:
  - Pipeline Health,
  - Connector Health,
  - Retrieval Quality,
  - Embedding/Model Cost,
  - Storage/Index Freshness,
  - Security/Audit Overview.
- Critical beta alerts for connector failure, Kafka lag, deadletter spikes, retrieval failures, model cost spikes, index staleness, and webhook signature failures.
- Ingestion lag metrics.
- Connector health.
- Backfill progress.
- Webhook delivery status.
- Deadletter/retry visibility.
- Index freshness.
- Permission snapshot freshness.
- Evidence-pack audit trail.
- Runbooks for connector failure, replay, and permission desync.

Validation:

- Simulated failed webhook appears in deadletter view.
- Replay rebuilds source objects from raw events.
- Source health reports stale data accurately.
- Redaction tests prevent logs/traces from including source snippets, OAuth tokens, private URLs, raw file contents, or embeddings.
- Alert-rule simulations cover Kafka lag, deadletters, retrieval failures, and connector failure.

## Phase 8.25: Runtime Deployment

Goal: package Cortex for simple beta deployment without requiring Kubernetes.

Deliverables:

- Container images for FastAPI API and worker roles.
- Docker Compose local stack for API, workers, Postgres, Kafka-compatible broker, Qdrant, object storage, and optional Redis.
- Health/readiness endpoints for API and worker heartbeat records for workers.
- Configuration model for simple hosted containers.
- Kubernetes-compatible service boundaries documented, but no required Kubernetes manifests for beta.

Validation:

- Docker Compose starts API and at least one worker.
- Each worker role can run independently.
- Health/readiness checks fail clearly when required dependencies are missing.
- Deployment docs state which services can scale horizontally.

## Phase 8.4: Layer-Later Platform Components

Goal: add production platform components only where they protect real beta
usage or make operations materially easier.

Deliverables:

- Redis or managed cache only for ephemeral state: rate-limit counters, short-lived locks, sessions, hot health snapshots, and temporary query results.
- Managed reverse proxy/ingress contract for TLS, request size limits, routing, compression, and load balancing.
- API/user/model-call rate limiting for expensive retrieval, embedding, model gateway, and connector endpoints.
- Simple background scheduler using worker cron plus Postgres lease/advisory-lock coordination.
- Backup/restore runbooks and smoke checks:
  - Postgres backup and restore,
  - object storage lifecycle and restore,
  - Qdrant/OpenSearch rebuild from raw events, source objects, chunks, and embeddings.
- Feature/config flags for dev workbench access, deterministic versus real embeddings, connector rollout, and gradual context-gate blocking.
- Admin/support endpoints or UI for connector re-sync, deadletter replay, force re-embed/re-index, and tenant/source health inspection.
- Documentation that Redis is not source of truth and Qdrant/OpenSearch are rebuildable indexes.
- Documentation that v1 does not use custom distributed storage or a custom single-leader control plane.

Validation:

- Rate-limit tests cover API, user, provider, and model-call limits.
- Scheduler lease tests prove only one retention/eval job executes at a time.
- Backup restore drill succeeds in a staging/local environment.
- Derived index rebuild reproduces expected retrieval eval results.
- Admin actions are audited and permission-gated.
- Feature flags default to safe production values.

## Phase 8.5: Dev Workbench

Goal: visually test the pipeline with deterministic mock data before live connectors are complete.

Deliverables:

- `GET /dev/workbench` internal UI, disabled unless `CORTEX_DEV_WORKBENCH_ENABLED=true`.
- `POST /dev/fixtures/reset` and `POST /dev/fixtures/seed`.
- `POST /dev/pipeline/run` and `GET /dev/pipeline/runs/{run_id}`.
- `POST /dev/retrieval/query`.
- `GET /dev/evidence-packs/{id}`.
- `POST /dev/evals/run`.
- Pipeline timeline: seed, ingest, Kafka event, normalize, chunk/OCR, embed, index, link, retrieve, gate.
- Retrieval inspector: query plan, filters, FTS candidates, vector candidates, merged candidates, relationships, final ranking.
- Evidence-pack viewer: claims, citations, stale/conflicting evidence, source coverage, token budget, gate status.

Validation:

- Dev endpoints are unavailable unless enabled.
- Fixture seed creates expected raw events, source objects, source files, chunks, embeddings, relationships, and evidence packs.
- Pipeline run is idempotent and traceable by generated IDs.
- Mock `COR-123` query returns Slack decision, diagram OCR, GitHub PR, Linear blocker, stale Redis doc, and `block`.
- Eval panel reports Recall@K, MRR, citation accuracy, conflict detection, gate accuracy, and latency.

## Phase 9: Minimal Web UI

Goal: audit and inspect, not replace the agent workflow.

Deliverables:

- Source health page.
- Evidence-pack inspector.
- Canonical decision history.
- Conflict/unresolved ambiguity list.
- Connector setup and source selection.
- Backfill/replay status.

Validation:

- Playwright smoke flow for source health and evidence-pack inspection.
- UI reads real store data.
- No static-only demo surfaces for core workflows.

## First Wow Demo Build Order

1. Seed production-shaped fixtures for Slack, Linear, GitHub, and docs.
2. Implement `/dev/workbench` and pipeline-run endpoints over deterministic fixtures.
3. Implement source objects, relationships, retrieval, and gate result over fixtures.
4. Demo query:

```text
I'm implementing Linear issue COR-123. What architecture decisions, diagrams,
Slack threads, PRs, and docs constrain this implementation, and is any of the
context stale or conflicting?
```

5. Return `STATUS: BLOCKED` because docs and Slack/GitHub/Linear disagree.
6. Show the workbench timeline from ingest through evidence pack.
7. Draft a canonical decision.
8. Approve it through MCP/CLI as if inside Codex/Claude Code.
9. Re-run retrieval and show the approved decision is now prioritized.
10. Replace fixtures with real Slack OAuth/backfill first.

## Carry Forward From CortexG

Useful to port conceptually:

- evidence pack shape,
- MCP tool family,
- source coverage diagnostics,
- artifact categories,
- source-aware chunking,
- retrieval scoring dimensions.

Avoid copying early:

- local JSON-store demo assumptions,
- broad app UI before connector/gate workflows,
- billing,
- many shallow connector stubs,
- local-only memory positioning,
- any implementation that cannot support raw-event replay and permission filtering.
