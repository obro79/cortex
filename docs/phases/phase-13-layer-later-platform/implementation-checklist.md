# Phase 13 Implementation Checklist

## Prerequisites

- [ ] Phase 10 admin authorization and audit primitives exist.
- [ ] Phase 11 observability conventions exist for logs, metrics, traces, and
      runbooks.
- [ ] Phase 12 API, worker, Compose, migration, and object storage paths are
      stable enough to extend.
- [ ] Production-like environment names and safe config defaults are documented.

## Cache and Redis

- [ ] Add an `EphemeralCacheService` interface.
- [ ] Add a local in-memory backend for tests and development.
- [ ] Add an optional Redis or managed-cache backend gated by config.
- [ ] Document allowed cache use cases.
- [ ] Document prohibited source-of-truth use cases.
- [ ] Add failure behavior for unavailable cache backends.
- [ ] Add metrics for cache operations, errors, and fallback behavior.

## Rate Limiting

- [ ] Define typed rate-limit policies.
- [ ] Add API/user/workspace rate-limit dimensions.
- [ ] Add provider connector rate-limit dimensions.
- [ ] Add embedding/model-call rate-limit dimensions.
- [ ] Add route middleware or dependency enforcement for protected endpoints.
- [ ] Add worker-side enforcement for connector and model calls.
- [ ] Emit structured logs and metrics on allow, deny, and backend failure.
- [ ] Return retry metadata for client-visible API limits.

## Scheduler

- [ ] Define scheduled job contract.
- [ ] Add Postgres lease or advisory-lock coordination.
- [ ] Add lease expiry and renewal behavior.
- [ ] Add idempotency keys or equivalent duplicate protection per job.
- [ ] Add periodic connector backfill job.
- [ ] Add retention or deletion completion job.
- [ ] Add source health snapshot job.
- [ ] Add eval or retrieval quality job if useful for Phase 13 validation.
- [ ] Add metrics for job start, success, failure, skipped lease, and duration.

## Backup, Restore, and Rebuild

- [ ] Write Postgres backup runbook.
- [ ] Write Postgres restore runbook.
- [ ] Write object storage lifecycle and restore runbook.
- [ ] Write derived index rebuild runbook.
- [ ] Add local or staging backup/restore smoke command.
- [ ] Add derived index rebuild smoke command.
- [ ] Add retrieval eval parity check after derived index rebuild.
- [ ] Record run evidence under this phase directory.

## Feature and Config Flags

- [ ] Consolidate typed feature/config flag access.
- [ ] Keep dev workbench disabled by default in production.
- [ ] Make deterministic versus real embeddings explicit.
- [ ] Add connector rollout flags by provider and, where needed, workspace.
- [ ] Add gradual context-gate blocking flag.
- [ ] Ensure optional Redis/cache behavior is explicit.
- [ ] Ensure sanitized config output includes safe flag state and redacts
      secrets.

## Support Operations

- [ ] Add permission-gated connector re-sync operation.
- [ ] Add permission-gated deadletter replay operation.
- [ ] Add permission-gated force re-embed operation.
- [ ] Add permission-gated force re-index operation.
- [ ] Add permission-gated tenant/source health inspection.
- [ ] Audit allowed and denied attempts.
- [ ] Avoid raw private content exposure in responses and logs.
- [ ] Add trace IDs to support operation logs where available.

## Ingress Contract

- [ ] Document TLS termination expectations.
- [ ] Document request size limits.
- [ ] Document routing and health/readiness paths.
- [ ] Document compression behavior.
- [ ] Document timeout behavior.
- [ ] Document load balancing assumptions.
- [ ] Document forwarded header handling.
- [ ] Add tests or config checks for app-level assumptions where practical.

## Final Review

- [ ] Run focused unit tests.
- [ ] Run backup/restore smoke.
- [ ] Run derived index rebuild smoke.
- [ ] Run retrieval eval parity check.
- [ ] Run pre-landing code review.
- [ ] Update phase docs with evidence and any deviations.
