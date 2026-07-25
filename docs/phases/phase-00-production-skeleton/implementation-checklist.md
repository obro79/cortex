# Phase 0 Implementation Checklist

## 1. Project Scaffold

- Create `pyproject.toml` with Python 3.12, package metadata, dependencies, dev
  dependencies, and console scripts.
- Create `README.md` with quickstart, commands, env vars, and Phase 0 non-goals.
- Create `.env.example`.
- Create `src/cortex/` package and test tree.
- Configure `ruff`, `mypy`, and `pytest`.

Acceptance:

- `python -m pip install -e ".[dev]"` works.
- `ruff check .`, `ruff format --check .`, `mypy src`, and `pytest` are valid commands.

## 2. Config And Observability

- Implement Pydantic settings in `src/cortex/config.py`.
- Add structured logging setup.
- Add OpenTelemetry initialization with no-op fallback.
- Add redaction helper for token, secret, payload, text, URL, and vector-like keys.

Acceptance:

- settings load with no `.env`,
- sanitized config output hides sensitive values,
- log redaction tests pass,
- OTEL endpoint is optional.

## 3. Contracts

- Implement status enums from `v1-entity-state-schema.md`.
- Implement `PipelineEventEnvelope` and nested models.
- Implement entity Pydantic stubs.
- Add helper ID/timestamp types where useful.

Acceptance:

- enum tests match doc values exactly,
- envelope validates required fields,
- forbidden content-bearing payload keys are rejected,
- entity stubs can serialize/deserialize representative examples.

## 4. Database And Migrations

- Add SQLAlchemy async engine/session factory.
- Add declarative base.
- Add Alembic config and `alembic/env.py`.
- Add initial no-op or smoke-table migration only if needed.

Acceptance:

- package imports without a database,
- DB session factory can be constructed from `DATABASE_URL`,
- Alembic config loads.

## 5. API Shell

- Implement FastAPI app factory.
- Add `GET /health/live`.
- Add `GET /health/ready`.
- Add gated dev router.

Acceptance:

- health tests pass with `httpx` test client,
- `/dev/workbench` is unavailable when disabled,
- `/dev/workbench` returns placeholder response when enabled.

## 6. CLI Shell

- Implement Typer app.
- Add `cortex doctor`.
- Add `cortex config`.

Acceptance:

- `cortex --help` exits 0,
- `cortex doctor` exits 0 locally,
- `cortex config` prints sanitized config only.

## 7. Worker Shell

- Implement `cortex-worker --role noop`.
- Load settings/logging/tracing.
- Exit cleanly for `noop`.

Acceptance:

- worker smoke test runs the noop role without external services.

## 8. MCP Shell

- Create MCP server module.
- Register future tool names:
  - `retrieve_context`,
  - `get_related_work`,
  - `check_context_gate`,
  - `propose_canonical_decision`,
  - `approve_canonical_decision`.
- Return structured not-implemented responses.

Acceptance:

- MCP module imports,
- tool names are discoverable in test,
- no retrieval behavior is faked.

## 9. Interfaces

- Add protocols:
  - `EventBus`,
  - `ObjectStorage`,
  - `Cache`,
  - `RateLimiter`,
  - `Scheduler`,
  - `VectorIndex`,
  - `Worker`.
- Add `InMemoryEventBus`.
- Add no-op/local placeholders where helpful.

Acceptance:

- interfaces have focused method sets,
- tests can publish events through `InMemoryEventBus`,
- unimplemented concrete adapters fail clearly.

## 10. Docker Compose

- Add services:
  - `api`,
  - `worker`,
  - `postgres`,
  - `redpanda`,
  - `qdrant`,
  - `minio`,
  - optional/profiled `redis`.

Acceptance:

- `docker compose config` passes,
- `docker compose up -d postgres` works on a prepared machine,
- tests do not require all containers.

## Completion Criteria

Phase 0 is complete when:

- all acceptance checks above pass,
- no real provider credentials are required,
- Phase 1 can add fixture seed/run endpoints without changing repo structure,
- Phase 2 can add `raw_events` without changing event/config abstractions.

