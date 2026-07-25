# ADR-020: Layered Platform Components

## Status

Accepted.

## Context

Cortex needs production credibility, but the first beta should not spend most of
its energy building platform infrastructure before the connector, retrieval, and
context-gate loops work. Some components are clearly needed later: cache,
ingress, rate limiting, background scheduling, backup/restore, feature flags,
and admin/support tools.

## Decision

Design the contracts now and layer the implementations as usage proves the need.

Initial design hooks:

- cache interface for ephemeral state,
- rate-limit policy model,
- scheduler/job contract,
- backup/restore runbooks,
- feature/config flag contract,
- admin action audit model.

Layered components:

- Redis or managed cache for rate-limit counters, short-lived locks, sessions,
  hot health snapshots, and temporary query results. It is not source of truth.
- Managed reverse proxy/ingress for TLS, request size limits, routing,
  compression, and load balancing. Cortex documents the requirement but does
  not custom-build ingress for beta.
- API/user/model-call rate limiting for expensive retrieval, embedding, model
  gateway, and connector endpoints.
- Background scheduler for periodic backfills, retention sweeps, deletion jobs,
  health checks, and eval runs. Start with a simple worker cron and lease.
- Backup/restore covering Postgres backups, object storage lifecycle/restore,
  and derived index rebuilds.
- Feature/config flags for dev workbench access, deterministic versus real
  embeddings, connector rollout, and gradual context-gate blocking.
- Admin/support tools for connector re-sync, deadletter replay, force
  re-embed/re-index, and tenant/source health inspection.

## Consequences

The system avoids overbuilding while still leaving clear extension points. Beta
can start with managed platform primitives and minimal internal controls.

The main risk is forgetting to add the hooks early. Phase 0 must include the
interfaces/config shapes even if the backing services are simple or stubbed.

