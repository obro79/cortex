# Phase 11 Test Plan

## Commands

```bash
ruff check .
ruff format --check .
mypy src
pytest
```

Focused local loop:

```bash
pytest tests/observability tests/operations tests/security tests/connectors tests/retrieval tests/context_gate
```

## Coverage Map

```txt
Tracing
  -> API
  -> webhooks/connectors
  -> Kafka producer/consumer
  -> workers
  -> retrieval/gate
  -> dev workbench

Logging
  -> required correlation fields
  -> redaction
  -> sanitized errors

Metrics
  -> connector health
  -> ingestion/Kafka lag
  -> worker throughput/deadletters
  -> retrieval/gate
  -> embedding/model cost
  -> index freshness
  -> permission/audit freshness

Dashboards
  -> metric references
  -> safe labels

Alerts
  -> connector failure
  -> Kafka lag
  -> deadletter spike
  -> retrieval failure
  -> model cost spike
  -> index staleness
  -> webhook signature failures

Operations
  -> admin authorization
  -> audit records
  -> replay/repair
  -> safe output
```

## Tests To Create

| Test file | Assertions |
| --- | --- |
| `tests/observability/test_trace_context.py` | Trace ID propagates across API, event envelope, worker, retrieval, and gate. |
| `tests/observability/test_structured_logs.py` | Required fields exist; source text/secrets/private URLs/embeddings are absent. |
| `tests/observability/test_metrics.py` | Metric names and labels are safe, low-cardinality, and emitted for core paths. |
| `tests/observability/test_otlp_exporter.py` | Local/test OpenTelemetry exporter smoke works with config on/off. |
| `tests/observability/test_dashboard_definitions.py` | Dashboard panels reference defined metrics and avoid unsafe labels. |
| `tests/observability/test_alert_rules.py` | Alert simulations cover required critical alerts and link runbooks. |
| `tests/operations/test_source_health.py` | Source health reports stale/failing providers accurately and safely. |
| `tests/operations/test_deadletter_replay.py` | Simulated failed webhook appears in deadletter view and can replay safely. |
| `tests/operations/test_repair_operations.py` | Force reprocess operations require admin authorization and audit records. |
| `tests/operations/test_evidence_pack_audit.py` | Evidence-pack audit trail is inspectable without leaking hidden content. |
| `tests/security/test_observability_redaction.py` | Logs, traces, metrics, dashboards, and run logs reject source snippets/tokens/private URLs/raw files/vectors. |

## Alert Simulation Matrix

| Alert | Simulation |
| --- | --- |
| Connector broken/OAuth revoked | Mark connector `needs_reauth`; expect alert. |
| Kafka lag above threshold | Emit lag metric above threshold; expect alert. |
| Worker deadletter spike | Create deadletter count spike; expect alert. |
| Retrieval failure spike | Emit retrieval failures over threshold; expect alert. |
| Model/embedding cost spike | Emit estimated spend over threshold; expect alert. |
| Index freshness stale | Mark Qdrant/index freshness stale; expect alert. |
| Webhook signature failure spike | Emit signature failures over threshold; expect alert. |
| Permission snapshot stale | Mark snapshot stale; expect alert or warning. |

## Redaction Assertions

Search logs, traces, metrics labels, dashboard definitions, alert annotations,
run logs, and operation responses for:

- OAuth tokens,
- provider webhook secrets,
- raw provider payloads,
- source snippets,
- OCR text,
- private URLs,
- file names from hidden sources,
- embeddings/vectors,
- full query text,
- non-allowlisted source names or debug IDs.

Expected result: no hits outside explicit protected storage boundaries.

## Runbook Validation

Each critical runbook should have:

- symptom,
- dashboard/alert link,
- safe commands/endpoints,
- permission requirement,
- repair steps,
- validation steps,
- escalation criteria,
- forbidden data exposure reminder.

## Not Required In Phase 11

- Public admin console,
- self-hosted observability stack,
- Kubernetes manifests/autoscaling,
- new connectors,
- full deletion/retention implementation,
- Phase 12 runtime packaging.
