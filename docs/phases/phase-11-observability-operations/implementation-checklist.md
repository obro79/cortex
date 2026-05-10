# Phase 11 Implementation Checklist

## 1. Observability Foundations

- Add OpenTelemetry setup with local/no-op defaults.
- Add trace context helpers.
- Add structured logging context helper.
- Add metric naming/label conventions.
- Reuse Phase 10 redaction helpers for logs/events/metrics.

Acceptance:

- traces can be enabled/disabled by config,
- logs include required correlation fields,
- sensitive fields are redacted before emission.

Commit:

- `phase 11: add observability foundations`

## 2. Trace Propagation

- Instrument FastAPI requests.
- Instrument OAuth callbacks and connector endpoints.
- Instrument Kafka producers/consumers.
- Instrument worker stages.
- Instrument retrieval, context gate, canonical memory, and dev workbench.

Acceptance:

- one trace links webhook/API intake to raw event, worker stages, retrieval, and
  gate where applicable,
- trace IDs are stored on relevant records.

Commit:

- `phase 11: add trace propagation`

## 3. Structured Logs And Redaction

- Add safe log context to API, connectors, workers, retrieval, gate, and admin
  operations.
- Remove or sanitize content-bearing log fields.
- Add tests that logs/traces do not include source snippets, tokens, private
  URLs, raw file contents, embeddings, vectors, file names, or hidden source IDs.

Acceptance:

- redaction tests pass,
- logs remain useful through IDs, counts, statuses, hashes, and trace IDs.

Commit:

- `phase 11: harden structured logs`

## 4. Metrics

- Add connector health metrics.
- Add ingestion lag and cursor freshness metrics.
- Add Kafka lag and worker throughput metrics.
- Add retry/deadletter metrics.
- Add retrieval/evidence/gate metrics.
- Add embedding/model cost metrics.
- Add storage/index freshness metrics.
- Add permission/audit freshness metrics.

Acceptance:

- metric labels are low-cardinality and safe,
- local/test exporter smoke passes.

Commit:

- `phase 11: add operational metrics`

## 5. Dashboards

- Add dashboard definitions for Pipeline Health.
- Add dashboard definitions for Connector Health.
- Add dashboard definitions for Retrieval Quality.
- Add dashboard definitions for Embedding/Model Cost.
- Add dashboard definitions for Storage/Index Freshness.
- Add dashboard definitions for Security/Audit Overview.

Acceptance:

- dashboards reference existing metrics,
- panels avoid unsafe labels/content,
- dashboard docs include intended operator questions.

Commit:

- `phase 11: add Grafana dashboard definitions`

## 6. Alerts

- Add alert catalog with thresholds, severity, owner/route, and runbook links.
- Add simulations for connector failure, Kafka lag, deadletter spike, retrieval
  failure spike, model cost spike, index staleness, and webhook signature
  failure spike.
- Add noise/suppression guidance.

Acceptance:

- alert simulations pass,
- every critical alert has an actionable runbook.

Commit:

- `phase 11: add beta alert rules`

## 7. Operations And Repair

- Add permission-gated operation summaries for tenant/source health.
- Add deadletter/retry summary views.
- Add replay verified deadletter operation.
- Add force re-normalize/re-chunk/re-embed/re-index operations where supported.
- Add evidence-pack audit trail inspection.

Acceptance:

- operations require Phase 10 admin authorization,
- actions create sanitized audit records,
- outputs contain no raw payloads or source content.

Commit:

- `phase 11: add operations and repair surfaces`

## 8. Runbooks And Review Evidence

- Add runbooks listed in [`plan.md`](plan.md).
- Add local smoke instructions for OpenTelemetry/test collector.
- Add Phase 11 run log template.
- Produce final observability review report.

Acceptance:

- runbooks cover connector failure, replay, and permission desync at minimum,
- final report records commands, simulations, redaction results, and residual
  risks.

Commit:

- `phase 11: document operations runbooks`

## Commit Cadence

Use separate commits:

1. Observability foundations.
2. Trace propagation.
3. Structured logs/redaction.
4. Metrics.
5. Dashboards.
6. Alerts.
7. Operations/repair surfaces.
8. Runbooks/review evidence.

Each commit should include focused tests or validation artifacts for its slice.
Do not combine instrumentation, dashboards, alerts, and repair endpoints in one
large diff.
