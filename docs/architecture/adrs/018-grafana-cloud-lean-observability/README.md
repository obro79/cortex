# ADR-018: Grafana Cloud Lean Observability

## Status

Accepted.

## Decision

Use OpenTelemetry instrumentation and Grafana Cloud managed metrics, logs, and
traces for design-partner beta observability.

## What It Is

Cortex services emit traces, metrics, structured logs, and error events from the
FastAPI API, Kafka workers, model gateway, retrieval service, context gate, and
dev workbench. Grafana Cloud provides the dashboards and alerting layer.

## Why Cortex Uses It

- Cortex has asynchronous ingestion and retrieval pipelines that need visibility.
- Managed observability avoids operating Prometheus, Loki, and Tempo early.
- Grafana dashboards make connector, worker, retrieval, and model-cost health
  visible without building a full ops UI first.

## Required Correlation Fields

- `trace_id`
- `workspace_id`
- `source_connection_id`
- `pipeline_run_id`
- `kafka_topic`
- `worker_name`
- `retrieval_request_id`
- `evidence_pack_id`

## Initial Dashboards

- Pipeline Health: webhook ingest, Kafka lag, worker throughput, deadletters,
  stage latency.
- Connector Health: OAuth status, backfill progress, cursor freshness, provider
  rate limits.
- Retrieval Quality: latency, no-result rate, gate allow/warn/block counts,
  eval scores.
- Embedding/Model Cost: job count, failures, provider latency, estimated spend.
- Storage/Index Freshness: Postgres, Qdrant, object storage, and future
  OpenSearch freshness.
- Security/Audit Overview: source allowlist changes, failed auth, delete/export
  requests, webhook signature failures.

## Initial Alerts

- Connector broken or OAuth revoked.
- Kafka lag above threshold.
- Worker deadletter spike.
- Retrieval error-rate spike.
- Model or embedding cost spike.
- Qdrant/index freshness stale.
- Webhook signature failure spike.

## Alternatives Considered

- Self-host Grafana, Prometheus, Loki, and Tempo.
- App-only structured logs plus dev workbench.
- Full SRE alerting from day one.

## Why Alternatives Lost

- Self-hosting observability adds operations burden before product validation.
- App-only logs are not enough once real connectors and workers run.
- Full SRE alerting creates noise and setup cost too early.

## Tradeoffs

- Grafana Cloud creates a vendor dependency.
- Managed observability has usage-based cost.
- Dashboards still need disciplined metric naming and trace propagation.

## Failure Modes

- Logs accidentally include source snippets, tokens, private URLs, or file names.
- Missing trace propagation makes pipeline debugging hard.
- Too many alerts train people to ignore them.

## How We Test It

- Trace propagation tests across mock pipeline stages.
- Redaction tests for logs and error events.
- Smoke export to a local OpenTelemetry collector or test endpoint.
- Alert-rule simulations for Kafka lag, deadletters, retrieval failures, and
  connector failure.

## How This Maps From CortexG

`cortexg` has source coverage and event/run records. Cortex adds standard
observability plumbing and Grafana dashboards around those concepts.

