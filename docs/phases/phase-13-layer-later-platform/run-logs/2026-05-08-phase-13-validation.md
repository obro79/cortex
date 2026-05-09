# Phase 13 Validation

Date: 2026-05-08

## Evidence

- Ephemeral cache contract has in-memory and injected Redis-compatible backends.
- Redis remains optional and documented as ephemeral only.
- API, provider connector, and embedding/model-call rate limits have focused
  tests.
- Singleton scheduler leases use a Postgres-backed lease model with fencing
  tokens and an in-memory test backend.
- Feature flags default to safe production values and production validation
  rejects unsafe combinations.
- Backup/restore and derived-index rebuild runbooks have static smoke commands.
- Support operations are permission-gated and audited without raw target IDs in
  audit records.
- Ingress contract documents TLS, forwarding, health, request-size, timeout, and
  content-leak boundaries.

## Validation Commands

```bash
uv run ruff format --check .
uv run ruff check .
uv run mypy src
uv run pytest
uv run python scripts/backup_restore_smoke.py --static
uv run python scripts/derived_index_rebuild_smoke.py --static
```

## Residual Notes

- Full backup/restore and derived-index rebuild drills require disposable local
  or staging infrastructure.
- Redis client construction is intentionally not a hard dependency; the Redis
  backend is dependency-injected until a production runtime wires a client.
