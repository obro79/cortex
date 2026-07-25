# Phase 13 Engineering Review

## Status

Approved for implementation with guardrails.

The plan matches ADR-020 and ADR-021: layer operational components only where
they protect beta usage, keep Postgres/Kafka/object storage authoritative, and
avoid custom distributed coordination.

## Required Guardrails

### Redis Boundary

Redis must never store authoritative records, cursors, permissions, audit logs,
raw events, normalized records, chunks, embeddings, or rebuild state.

Allowed uses:

- rate-limit counters,
- short-lived locks,
- health snapshots,
- temporary query results,
- sessions if required by hosted auth.

Tests should prove the app can recover or continue safely after cache loss.

### Rate-Limit Consistency

Rate limiting needs one shared policy model used by both API and worker paths.
Avoid per-route hard-coded thresholds.

At minimum cover:

- API request limits,
- user/workspace limits,
- provider limits,
- embedding/model-call limits.

Denied API requests should include retry metadata. Worker denials should produce
retryable job outcomes where appropriate.

### Scheduler Correctness

The scheduler must be boring:

- Postgres lease or advisory lock coordination,
- lease expiry,
- no custom leader process,
- idempotent jobs,
- metrics for skipped/acquired/released/failed jobs.

The key test is two workers racing for the same job with only one execution.

### Backup and Rebuild Evidence

Docs alone are not enough. Phase 13 needs runnable smoke checks and recorded
evidence for:

- Postgres restore,
- object storage restore,
- derived index rebuild,
- retrieval eval parity after rebuild.

If a full staging drill is unavailable, record a local drill and the exact gap.

### Feature Flags

Feature flags should be typed, centralized, and safe by default.

Required flags:

- dev workbench,
- deterministic versus real embeddings,
- connector rollout,
- context-gate blocking rollout,
- optional cache/Redis behavior.

The sanitized config path should expose non-secret flag state for debugging.

### Support Operations

Support operations are security-sensitive. They must use the same authorization
and audit path as other admin actions.

Required operations:

- connector re-sync,
- deadletter replay,
- force re-embed,
- force re-index,
- tenant/source health inspection.

Denied attempts must be audited. Responses must avoid raw private content.

## Failure Modes to Test

- Redis unavailable at startup.
- Redis unavailable mid-request.
- Two schedulers race for the same job.
- Lease holder crashes before completing a job.
- Provider/model-call rate limit reached during worker processing.
- Feature flag missing or malformed.
- Unauthorized support operation attempt.
- Derived index missing or corrupted before rebuild.
- Backup restore succeeds but retrieval eval parity fails.

## Performance Notes

- Rate-limit checks are on hot paths; keep them low-latency and bounded.
- Scheduler polling must avoid tight loops and noisy logs.
- Support operations that enqueue large repair work should return job references,
  not block request threads.
- Rebuild smokes should use representative fixtures and leave full rebuilds for
  controlled drills.

## Implementation Sequence

1. Add typed feature/config access first so later work has a stable switchboard.
2. Add cache interface and local backend.
3. Add optional Redis backend.
4. Add shared rate-limit policy and API enforcement.
5. Extend rate limits to provider/model-call paths.
6. Add scheduler lease model and singleton job runner.
7. Add backup/restore and rebuild smoke commands.
8. Add support operations behind authorization and audit.
9. Document ingress contract and update runbooks.
10. Run focused validation and record evidence.

## Review Checklist

- [ ] No Redis authority leak.
- [ ] No custom leader election.
- [ ] No support operation bypasses authorization.
- [ ] No unaudited sensitive admin action.
- [ ] No raw private content in support logs or responses.
- [ ] Rate-limit policy is shared and typed.
- [ ] Scheduler singleton behavior has a contention test.
- [ ] Backup/restore smoke produces evidence.
- [ ] Derived index rebuild smoke produces eval evidence.
- [ ] Feature flags default to production-safe values.
