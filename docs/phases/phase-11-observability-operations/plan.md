# Phase 11 Plan: Observability And Operations

## Goal

Make Cortex understandable and recoverable in beta:

```txt
API / connectors / workers / retrieval / gate
  -> OpenTelemetry traces
  -> structured redacted logs
  -> metrics
  -> Grafana Cloud dashboards
  -> beta alerts
  -> replay/repair operations
  -> runbooks
```

Phase 11 is not a product UI phase. It gives operators enough visibility to
trust freshness, diagnose failures, and repair pipeline state without exposing
source content, secrets, hidden source identifiers, private URLs, raw payloads,
embeddings, or vectors.

## Inputs

- [`../implementation-roadmap.md`](../implementation-roadmap.md#phase-11-observability-and-operations)
- [`../../architecture/handbook.md`](../../architecture/handbook.md#observability)
- [`../../architecture/review.md`](../../architecture/review.md#observability-and-logging)
- [`../../architecture/adrs/018-grafana-cloud-lean-observability/README.md`](../../architecture/adrs/018-grafana-cloud-lean-observability/README.md)
- [`../../architecture/adrs/015-rate-limits-backpressure-repair/README.md`](../../architecture/adrs/015-rate-limits-backpressure-repair/README.md)
- [`../../architecture/pipeline-event-envelope.md`](../../architecture/pipeline-event-envelope.md)
- [`../phase-10-permissions-security/plan.md`](../phase-10-permissions-security/plan.md)

## Existing Foundation

Earlier phases provide:

- trace IDs and pipeline event envelopes,
- connector health and source coverage records,
- retry/deadletter state,
- retrieval requests and evidence packs,
- context gate results,
- admin authorization and audit logging,
- redaction/debug safety rules,
- replayable raw-event and derived pipeline stages.

Phase 11 should standardize instrumentation around those records rather than
invent new operational state.

## Non-Goals

- No full public admin console.
- No self-hosted Prometheus/Loki/Tempo stack.
- No Kubernetes autoscaling or deployment manifests; Phase 12 owns runtime
  packaging.
- No new source connectors.
- No new permission model.
- No dashboards that require source text, snippets, private URLs, file names, or
  raw payloads.

## Architecture

```txt
ObservabilityService
  -> OpenTelemetry setup
  -> trace context helpers
  -> metric emitters
  -> structured log context

OperationsService
  -> source health summary
  -> deadletter/retry views
  -> replay/repair commands
  -> index freshness checks
  -> permission snapshot freshness checks

AlertRuleCatalog
  -> beta alert definitions
  -> simulation fixtures
  -> runbook links

RunbookLibrary
  -> connector failure
  -> replay/deadletter repair
  -> permission desync
  -> index staleness
  -> retrieval failures
```

Every operational action that changes state must reuse Phase 10 admin
authorization and audit logging.

## Required Correlation Fields

Structured logs, metrics labels where safe, traces, and operation records should
carry:

- `trace_id`,
- `workspace_id`,
- `source_connection_id`,
- `pipeline_run_id`,
- `kafka_topic`,
- `worker_name`,
- `retrieval_request_id`,
- `evidence_pack_id`.

Do not log full query text, source text, snippets, OCR text, raw payloads,
tokens, private URLs, embeddings, vectors, non-allowlisted source names, file
names, or hidden debug IDs.

## Instrumentation Scope

Add OpenTelemetry traces and structured logs across:

- FastAPI request lifecycle,
- OAuth callbacks and connector health endpoints,
- provider backfills and webhooks,
- Kafka producers/consumers,
- normalization/chunking/embedding/index workers,
- relationship builder,
- retrieval service,
- context gate service,
- canonical memory approval flow,
- dev workbench pipeline runs,
- admin/operations actions.

Trace propagation must preserve `trace_id` from inbound API/webhook through raw
event, worker stages, retrieval, gate, and audit records.

## Metrics

Emit safe metrics for:

- webhook ingest count/error/latency,
- Kafka consumer lag by topic/group,
- worker throughput and stage latency,
- retry/deadletter counts,
- backfill progress and cursor freshness,
- provider rate-limit events,
- OAuth status and scope drift counts,
- source coverage/freshness,
- retrieval latency/error/no-result rate,
- gate allow/warn/block counts,
- embedding/model job count/failure/latency/cost estimate,
- index freshness for Postgres FTS, Qdrant, and future OpenSearch,
- permission snapshot freshness,
- audit/security event counts.

Metric labels must be low-cardinality and safe. Use provider, stage, status,
worker, topic, and coarse source type labels. Avoid raw source names, URLs,
external IDs, query text, file names, and tenant-specific content labels.

## Grafana Cloud Dashboards

Create lean beta dashboards:

1. Pipeline Health
   - webhook ingest,
   - Kafka lag,
   - worker throughput,
   - stage latency,
   - retry/deadletter counts.
2. Connector Health
   - OAuth status,
   - source connection status,
   - backfill progress,
   - cursor freshness,
   - provider rate limits.
3. Retrieval Quality
   - latency,
   - error rate,
   - no-result rate,
   - evidence-pack creation count,
   - gate allow/warn/block counts,
   - eval score summaries.
4. Embedding/Model Cost
   - job count,
   - provider failures,
   - latency,
   - estimated spend,
   - stale embedding backlog.
5. Storage/Index Freshness
   - raw event lag,
   - chunk/index job freshness,
   - Postgres FTS/Qdrant freshness,
   - object storage errors,
   - cleanup/deletion queue status.
6. Security/Audit Overview
   - source allowlist changes,
   - failed auth/admin attempts,
   - connector reauth/revoke events,
   - debug export attempts,
   - webhook signature failures,
   - permission snapshot freshness.

Dashboards should link to runbooks and use safe identifiers only.

## Beta Alerts

Add initial critical alerts:

- connector broken or OAuth revoked,
- Kafka lag above threshold,
- worker deadletter spike,
- retrieval error-rate spike,
- model/embedding cost spike,
- Qdrant/index freshness stale,
- webhook signature failure spike,
- permission snapshot stale,
- evidence-pack creation failure spike.

Every alert must have:

- owner/route,
- severity,
- threshold,
- suppression/noise guidance,
- runbook link,
- simulation test.

Avoid broad noisy alerts that do not have an operator action.

## Operations And Repair

Expose permission-gated operations for:

- inspect tenant/source health,
- inspect pipeline run,
- inspect deadletter/retry summaries,
- replay verified deadletters,
- re-run connector sync,
- force re-normalize/re-chunk/re-embed/re-index,
- run retrieval evals,
- inspect evidence-pack audit trail,
- trigger permission snapshot refresh,
- start deletion/retention repair when that workflow exists.

Do not expose raw payloads or source content in operational outputs. Use record
IDs, trace IDs, hashes, counts, statuses, sanitized error codes, and replay
hints.

## Runbooks

Create runbooks for:

- connector failure or OAuth revoked,
- webhook signature failures,
- Kafka lag,
- worker deadletter spike,
- replay deadletter safely,
- provider rate limit/backpressure,
- retrieval failures/no-result spike,
- index freshness stale,
- embedding/model cost spike,
- permission desync or stale permission snapshots,
- evidence-pack audit investigation.

Each runbook should include symptoms, likely causes, dashboards to inspect,
commands/endpoints, safe data boundaries, rollback/repair steps, and validation.

## Acceptance Criteria

Phase 11 is complete when:

- traces propagate across API, connectors, workers, retrieval, gate, and dev
  workbench,
- structured logs include required correlation fields and pass redaction tests,
- metrics exist for connector health, ingestion lag, Kafka lag, workers,
  retrieval, gate, embeddings, index freshness, permissions, and audit events,
- Grafana Cloud dashboard definitions exist for the six beta dashboards,
- alert-rule simulations cover Kafka lag, deadletters, retrieval failures,
  connector failure, model cost spike, index staleness, and webhook signature
  failures,
- permission-gated replay/repair operations are auditable,
- runbooks exist for connector failure, replay, and permission desync,
- no logs/traces/metrics/dashboards/runbooks expose source snippets, OAuth
  tokens, private URLs, raw file contents, embeddings, vectors, or hidden source
  identifiers.
