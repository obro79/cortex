# Production Operations Runbook

This runbook defines the minimum hosted beta operating model for Cortex.

## Topology

- `api`: stateless FastAPI service behind managed HTTPS ingress.
- `worker-pipeline`: Kafka consumer group for normalization, chunking,
  embedding, and downstream pipeline events.
- `worker-lifecycle`: queued deletion/export worker for lifecycle compliance
  jobs.
- `migrate`: explicit one-shot Alembic migration job.
- Postgres: source of truth for tenant, connector, audit, job, retrieval, and
  billing/lifecycle state.
- Kafka: pipeline event transport, not the long-term source of truth.
- Object storage: raw payload and file pointer storage.
- Qdrant or compatible vector index: derived retrieval index.
- Grafana Cloud or OTLP-compatible backend: metrics, traces, and logs.

## CI/CD

Required gates before deploy:

- `uv run --extra dev ruff check .`
- `uv run --extra dev ruff format --check .`
- `uv run --extra dev mypy src`
- `uv run --extra dev pytest`
- container build validation,
- migration dry-run review for schema changes.

Deploy order:

1. Build and publish immutable images.
2. Run `migrate` once against the target database.
3. Deploy `api`.
4. Deploy `worker-pipeline`.
5. Deploy `worker-lifecycle` when lifecycle queueing is enabled.
6. Verify readiness, worker logs, Kafka topic access, lifecycle queue drain, and
   connector smoke.

## Migration Strategy

- Migrations are never run implicitly by API or worker startup.
- Roll forward is preferred for additive migrations.
- Rollback requires a named owner, backup reference, migration revision, and
  explicit decision record.
- Data-destructive migrations require a restore point and staging rehearsal.

## Alerts

Minimum alert rules:

- API readiness failing for 5 minutes.
- Worker consumer lag above the beta SLO for 10 minutes.
- Deadletter count increasing for 10 minutes.
- Postgres connection exhaustion or sustained error rate.
- Payload/object storage write failures.
- Provider webhook signature failures above baseline.
- Provider ACL stale or missing snapshot alerts above baseline.
- Lifecycle deletion/export failures or stuck leases.
- Error rate above beta SLO by service.

## Support Diagnostics

Support diagnostics may include:

- workspace ID,
- actor ID,
- trace ID,
- source connection ID hashes,
- counts, statuses, timestamps, and error codes.

Support diagnostics must not include:

- provider tokens,
- session tokens,
- raw message or document content,
- private file URLs,
- unredacted customer object IDs when a hash is sufficient.

## Load And Cost Tests

Beta load test:

- seed one workspace with representative Slack, GitHub, Linear, and repo-docs
  fixture events,
- run the pipeline to completion,
- run retrieval smoke queries,
- record API p95, worker lag, deadletters, Postgres CPU, queue depth, model
  calls, and storage growth.

Cost test:

- record model calls, storage growth, database size, worker runtime, and
  provider API calls per fixture workspace,
- compare against plan limits and expected beta packaging.

## Rollback

Rollback sequence:

1. Stop new deploy rollout.
2. Disable risky connector/backfill feature flags if needed.
3. Roll API and worker images back to the last known-good image.
4. Do not downgrade schema unless a reviewed downgrade plan exists.
5. Restore from backup only when data corruption is confirmed and approved.
6. Record customer impact, timeline, owner, and follow-up fixes.

## Drill Evidence

Every production drill record must include:

- date,
- environment,
- owner,
- commands or workflow URLs,
- result,
- residual risks,
- follow-up issues.
