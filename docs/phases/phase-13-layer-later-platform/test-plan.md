# Phase 13 Test Plan

## Focus

Phase 13 testing proves that the new platform layers protect the system without
creating new authority paths. The main risks are over-reliance on Redis, duplicate
singleton jobs, invisible rate-limit failures, unsafe production defaults, and
unaudited support operations.

## Automated Tests

Suggested focused test files:

- `tests/platform/test_ephemeral_cache.py`
- `tests/platform/test_redis_not_source_of_truth.py`
- `tests/rate_limit/test_rate_limit_policy.py`
- `tests/rate_limit/test_api_user_provider_model_limits.py`
- `tests/scheduler/test_postgres_lease.py`
- `tests/scheduler/test_singleton_jobs.py`
- `tests/platform/test_feature_flags.py`
- `tests/platform/test_ingress_contract.py`
- `tests/backup/test_postgres_restore_smoke.py`
- `tests/backup/test_object_storage_restore_smoke.py`
- `tests/indexing/test_derived_index_rebuild.py`
- `tests/admin/test_support_operations_auth_audit.py`

## Required Coverage

### Cache

- In-memory cache supports get, set, increment, delete, TTL expiry, and lock
  semantics needed by callers.
- Optional Redis backend is selected only when configured.
- Cache loss does not lose authoritative data.
- Cache unavailable behavior is explicit and observable.

### Rate Limits

- API route limits deny requests after configured thresholds.
- User/workspace limits are isolated from each other.
- Provider limits protect Slack, GitHub, Linear, and repo docs calls where
  applicable.
- Embedding/model-call limits protect expensive model gateway paths.
- Denied API requests include retry metadata.
- Rate-limit decisions emit metrics and structured logs.

### Scheduler

- Two workers racing for the same singleton job result in one execution.
- Expired leases can be recovered.
- Active leases are not stolen.
- Job retries are idempotent.
- Skipped lease attempts are logged and counted.

### Backup, Restore, and Rebuild

- Postgres backup/restore smoke succeeds in local or staging.
- Object storage restore smoke succeeds for representative payloads.
- Qdrant/OpenSearch derived index rebuild starts from authoritative records and
  durable payloads, not stale index data.
- Retrieval eval results after rebuild match expected fixtures within the
  documented tolerance.

### Feature Flags

- Production defaults disable dev workbench and unsafe optional behavior.
- Connector rollout flags default to off unless explicitly enabled.
- Deterministic versus real embeddings is explicit.
- Context-gate blocking can roll out separately from scoring/evaluation.
- Sanitized config output reports flag state without exposing secrets.

### Support Operations

- Unauthorized support operations are denied and audited.
- Authorized support operations are audited.
- Re-sync, deadletter replay, force re-embed, and force re-index validate target
  scope before enqueueing work.
- Responses and logs avoid raw private content.

### Ingress Contract

- App-level request size assumptions match documented ingress limits.
- Health and readiness routes are stable.
- Forwarded header handling is deterministic behind a managed proxy.
- Timeout assumptions are documented and covered by at least one integration or
  config test.

## Suggested Commands

```bash
ruff check src tests
mypy src
pytest tests/platform tests/rate_limit tests/scheduler tests/admin
pytest tests/backup tests/indexing tests/dev
```

Run the full suite before closing the phase if the implementation touches shared
API, worker, config, or persistence behavior.

## Manual Drills

- Local or staging Postgres backup/restore drill.
- Object storage restore drill for at least one file payload and one normalized
  payload.
- Derived index rebuild drill followed by retrieval eval parity check.
- Scheduler contention drill with two worker processes.
- Rate-limit drill across API, provider, and model-call limits.
- Support operation drill confirming authorization, audit logs, metrics, and
  absence of raw private content.

## Exit Evidence

Record evidence in this phase directory:

- command outputs or summarized run logs,
- backup/restore timestamps and target environment,
- rebuild eval result IDs,
- screenshots or API responses for support operations if helpful,
- known gaps and follow-up issues.
