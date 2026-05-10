# Phase 13 Plan: Layer-Later Platform Components

## Goal

Add the smallest platform components needed to protect beta usage and make
operations repeatable: ephemeral cache hooks, rate limits, singleton scheduling,
backup/restore drills, feature/config flags, managed ingress contracts, and
permission-gated support operations.

This phase is successful when Cortex can run real beta traffic with clear limits,
recoverable data paths, audited operational controls, and no accidental new
source-of-truth system.

## Inputs

- [`../implementation-roadmap.md`](../implementation-roadmap.md#phase-13-layer-later-platform-components)
- [`../../architecture/handbook.md`](../../architecture/handbook.md#layer-later-platform-components)
- [`../../architecture/adrs/020-layered-platform-components/README.md`](../../architecture/adrs/020-layered-platform-components/README.md)
- [`../../architecture/adrs/021-distributed-coordination-without-custom-leader/README.md`](../../architecture/adrs/021-distributed-coordination-without-custom-leader/README.md)
- Phase 10 permissions and admin audit plan
- Phase 11 observability and operations plan
- Phase 12 runtime and deployment plan

## Non-Goals

- Do not make Redis a source of truth.
- Do not build custom distributed storage.
- Do not build a custom single-leader control plane.
- Do not require Temporal, Kubernetes CronJobs, or a hosted feature flag vendor
  for v1.
- Do not build a public admin console; keep support tools internal,
  permission-gated, and auditable.
- Do not automate every disaster recovery path before the manual runbooks and
  smoke drills are proven.

## Existing Foundation

- `src/cortex/config.py` already exposes environment, connector, Redis, object
  storage, Qdrant, Kafka, database, and OpenTelemetry settings.
- Phase 10 defines admin authorization and audit expectations for sensitive
  operations.
- Phase 11 defines logs, metrics, traces, dashboards, alerts, runbooks, and
  repair flows.
- Phase 12 defines the packaged API, pipeline worker role, Compose stack, object
  storage, and migration discipline.

## Architecture

Phase 13 should introduce narrow services with local defaults and managed
production escape hatches:

```text
Managed ingress / reverse proxy
        |
        v
FastAPI routes and worker entrypoints
        |
        +--> RateLimitService
        |       +--> EphemeralCacheService
        |              +--> in-memory dev backend
        |              +--> optional Redis / managed cache backend
        |
        +--> FeatureFlagService
        |
        +--> AdminAuthorizationService
        |       +--> AuditLog
        |       +--> SupportOpsService
        |
        +--> SchedulerService
                +--> Postgres lease/advisory-lock coordination
                +--> idempotent jobs
```

## Workstreams

### 1. Ephemeral Cache Contract

Add a small cache interface for transient state only:

- rate-limit counters,
- short-lived coordination locks when Postgres leases are not the better fit,
- sessions if needed by hosted auth,
- hot health snapshots,
- temporary query results.

The cache must be safe to lose. Production may use Redis or a managed cache, but
local development must work without Redis.

### 2. Rate Limiting

Add a policy model and enforcement layer for expensive and externally constrained
paths:

- API route limits,
- user/workspace limits,
- provider connector limits,
- embedding/model-call limits,
- retrieval/model gateway limits.

Limit responses must be deterministic, observable, and friendly enough for
clients to retry. Counters should use Redis when configured and a local backend
for tests/dev.

### 3. Scheduler and Singleton Jobs

Implement a simple scheduler using worker cron plus Postgres lease or advisory
lock coordination. Jobs must be idempotent and safe under retries.

Initial jobs:

- periodic connector backfills,
- retention sweeps,
- deletion completion checks,
- source health snapshots,
- eval or retrieval quality runs where useful.

Postgres is the first coordination mechanism. Redis locks are acceptable later
only for short-lived coordination after Redis already exists for rate limits.

### 4. Backup, Restore, and Rebuild

Create runbooks and smoke checks for:

- Postgres backup and restore,
- object storage lifecycle and restore,
- derived index rebuild for Qdrant/OpenSearch from source objects, raw events,
  chunks, embeddings, and normalized records,
- retrieval eval parity after rebuild.

The documented recovery model must state that Qdrant/OpenSearch are rebuildable
indexes, not authoritative storage.

### 5. Feature and Config Flags

Consolidate a typed feature flag contract with safe production defaults:

- dev workbench disabled in production,
- deterministic versus real embeddings explicit,
- connector rollout controlled per provider/workspace,
- gradual context-gate blocking controlled separately from scoring,
- optional platform components disabled unless configured.

Flags should be visible in sanitized config output without leaking secrets.

### 6. Support Operations

Add internal support operations behind Phase 10 authorization and audit:

- connector re-sync,
- deadletter replay,
- force re-embed,
- force re-index,
- tenant/source health inspection.

Support operations must not expose raw private content by default. Every allowed
or denied sensitive action must be audited with actor, action, target, result,
and trace context where available.

### 7. Ingress Contract

Document the managed reverse proxy or ingress expectations:

- TLS termination,
- request size limits,
- routing,
- compression,
- timeout behavior,
- load balancing,
- forwarded header handling,
- health and readiness paths.

This phase documents and tests app assumptions; it does not require building a
custom ingress controller.

## Commit Cadence

1. Cache contract and local backend.
2. Optional Redis backend and cache docs.
3. Rate-limit policy model and API enforcement.
4. Provider/model-call rate-limit enforcement.
5. Scheduler lease model and singleton job runner.
6. Feature flag contract and safe production defaults.
7. Backup/restore runbooks and smoke scripts.
8. Derived index rebuild smoke and retrieval eval parity check.
9. Permission-gated support operations and audit coverage.
10. Ingress contract docs and final phase review evidence.

## Acceptance Criteria

- Rate-limit tests cover API, user/workspace, provider, and model-call limits.
- Scheduler lease tests prove only one singleton job executes at a time.
- Backup/restore drill succeeds in local or staging and records evidence.
- Derived index rebuild reproduces expected retrieval eval results.
- Admin/support operations are permission-gated and audited.
- Feature flags default to safe production values.
- Docs clearly state Redis is ephemeral and Qdrant/OpenSearch are rebuildable.
- Docs clearly state v1 avoids custom distributed storage and custom leader
  election.
