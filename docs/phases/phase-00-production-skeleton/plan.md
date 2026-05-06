# Phase 0 Plan: Production Skeleton

## Goal

Create the production-shaped Python repo skeleton without building the product
workflow yet. Phase 0 should leave the codebase ready for Phase 1 fixtures and
Phase 2 raw-event pipeline work.

The success bar is not "Cortex works." The success bar is "future phases can add
features without rethinking project structure, contracts, test setup, worker
entrypoints, config, or observability basics."

## Scope

Build now:

- Python/FastAPI app shell.
- Pydantic contract package.
- SQLAlchemy/Alembic migration shell.
- API and worker entrypoints.
- CLI and MCP server shells.
- Config/settings model.
- Pipeline event envelope models.
- V1 entity status enums and model stubs.
- Storage, cache, rate-limit, scheduler, worker, and event-bus interfaces.
- Local Docker Compose stack.
- OpenTelemetry/logging hooks.
- Minimal test framework and smoke tests.

Do not build yet:

- real Slack OAuth or webhooks,
- real ingestion pipeline,
- real normalization/chunking/retrieval/gate behavior,
- real Qdrant indexing beyond interface wiring,
- production auth,
- admin UI,
- Kubernetes/Temporal/custom Redis dependency.

## Tech Decisions

Use:

- Python 3.12.
- FastAPI for HTTP API.
- Pydantic v2 for contracts/settings.
- SQLAlchemy 2.x async ORM/Core.
- Alembic for migrations.
- `asyncpg` for Postgres driver.
- `pytest`, `pytest-asyncio`, and `httpx` for tests.
- `ruff` for lint/format.
- `mypy` for typing.
- `typer` for CLI.
- OpenTelemetry Python SDK with no-op/local defaults.
- Docker Compose for local Postgres, Kafka-compatible broker, Qdrant, object storage, and optional Redis.

Default local infrastructure:

- Postgres for app database.
- Redpanda as Kafka-compatible broker.
- Qdrant for vector DB container.
- MinIO for object-storage-compatible local blob storage.
- Redis container is optional and not required by tests.

## Repo Layout

Create this structure:

```txt
cortex/
  pyproject.toml
  README.md
  .env.example
  docker-compose.yml
  alembic.ini
  alembic/
    env.py
    versions/
  src/cortex/
    __init__.py
    api/
      __init__.py
      app.py
      routes/
        __init__.py
        health.py
        dev.py
    cli/
      __init__.py
      main.py
    config.py
    contracts/
      __init__.py
      enums.py
      ids.py
      pipeline_events.py
      entities.py
    db/
      __init__.py
      base.py
      session.py
      models.py
    events/
      __init__.py
      bus.py
      in_memory.py
    interfaces/
      __init__.py
      cache.py
      rate_limit.py
      scheduler.py
      storage.py
      vector_index.py
      worker.py
    mcp/
      __init__.py
      server.py
    observability/
      __init__.py
      logging.py
      tracing.py
    workers/
      __init__.py
      main.py
  tests/
    conftest.py
    contracts/
      test_pipeline_event_envelope.py
      test_entity_status_enums.py
    api/
      test_health.py
      test_dev_guard.py
    smoke/
      test_cli.py
      test_worker.py
      test_mcp.py
```

## Contracts

Implement contract models from the docs, but keep fields broad enough for Phase
1/2 to fill behavior later.

### Status Enums

Define string enums matching
[`v1-entity-state-schema.md`](../../architecture/v1-entity-state-schema.md):

- `RawEventStatus`
- `SourceObjectStatus`
- `SourceChunkStatus`
- `EmbeddingJobStatus`
- `IndexJobStatus`
- `EvidencePackStatus`
- `ContextGateStatus`
- `ApprovalStatus`
- `DeletionRequestStatus`

Tests must assert enum values exactly match the docs.

### Pipeline Event Envelope

Implement `PipelineEventEnvelope` from
[`pipeline-event-envelope.md`](../../architecture/pipeline-event-envelope.md).

Core Pydantic models:

- `PipelineEventEnvelope`
- `PipelineSubject`
- `PipelineCausation`
- `PipelineVersions`
- `PipelineHashes`
- `PipelineTrace`
- `PipelineProducer`
- `PipelineRetry`

Required validation:

- `schema_version == "pipeline-event-v1"`.
- `event_id`, `event_type`, `workspace_id`, `partition_key`, `subject`, and
  `trace.trace_id` are required.
- `payload` defaults to `{}`.
- content-bearing fields are not allowed in `payload` for known forbidden keys:
  `raw_payload`, `source_text`, `chunk_text`, `ocr_text`, `embedding`,
  `vector`, `oauth_token`, `secret`.

### Entity Stubs

Define Pydantic models for:

- `RawEvent`
- `SourceObject`
- `SourceFile`
- `SourceChunk`
- `EmbeddingRecord`
- `IndexJob`
- `RetrievalRequest`
- `EvidencePack`
- `ContextGateResult`
- `CanonicalDecision`
- `ApprovalRecord`
- `DeletionRequest`
- `DeletionTombstone`

Phase 0 does not need complete business logic. It does need stable field names,
IDs, timestamps, status fields, hashes, versions, and metadata placeholders.

## Database

Set up SQLAlchemy and Alembic but do not create all production migrations yet.

Build:

- async engine/session factory,
- declarative base,
- migration environment,
- one initial migration with minimal infrastructure tables:
  - `schema_migrations` is handled by Alembic,
  - `health_checks` or equivalent smoke table is optional,
  - no full domain table set unless implementation is ready to maintain it.

Reason: Phase 0 should validate DB wiring without prematurely freezing all table
details. Phase 2 can add `raw_events`; Phase 3 can add `source_objects`.

## API

FastAPI app:

- `GET /health/live`: returns process liveness.
- `GET /health/ready`: checks settings load and optional DB connectivity when configured.
- `/dev/*` routes are registered only when `CORTEX_DEV_WORKBENCH_ENABLED=true`.

Dev guard behavior:

- when disabled, `/dev/*` returns 404 or is not mounted,
- when enabled, `GET /dev/workbench` may return a placeholder HTML/text response.

## Worker Shell

Create a worker entrypoint that can run a named worker role:

```bash
cortex-worker --role noop
```

Phase 0 worker behavior:

- loads settings,
- initializes logging/tracing,
- starts and exits cleanly for `noop`,
- exposes a placeholder interface for future Kafka consumers.

No real Kafka consumption yet.

## Event Bus

Create an `EventBus` protocol/interface:

```python
class EventBus(Protocol):
    async def publish(self, event: PipelineEventEnvelope) -> None: ...
```

Implement:

- `InMemoryEventBus` for tests.
- `KafkaEventBus` placeholder that raises `NotImplementedError` or is behind an
  explicit config guard.

Phase 2 owns real Kafka publication.

## Interfaces

Create protocols plus no-op/local defaults:

- `ObjectStorage`: put/get/delete payload refs.
- `Cache`: get/set/delete for ephemeral state.
- `RateLimiter`: check/record calls.
- `Scheduler`: enqueue/schedule named jobs.
- `VectorIndex`: ensure collection, upsert, delete, search, health.
- `Worker`: start/stop lifecycle.

These should be thin interfaces, not implementations pretending to be complete.

## Config

Use Pydantic settings.

Required settings:

```txt
CORTEX_ENV=local
CORTEX_LOG_LEVEL=INFO
CORTEX_DEV_WORKBENCH_ENABLED=false
DATABASE_URL=
KAFKA_BOOTSTRAP_SERVERS=
OBJECT_STORAGE_ENDPOINT=
QDRANT_URL=
REDIS_URL=
OTEL_EXPORTER_OTLP_ENDPOINT=
```

Rules:

- local tests must pass without real external services,
- missing optional infrastructure should not crash import-time code,
- production mode may require stricter validation later.

## Observability

Implement:

- structured logging setup,
- trace ID helper,
- OpenTelemetry initialization with no-op fallback,
- log redaction helper for common secret/content fields.

Tests:

- redaction removes token/secret-like keys,
- logging setup does not require OTEL endpoint.

## CLI

Use Typer.

Commands:

```bash
cortex --help
cortex doctor
cortex config
```

Phase 0 behavior:

- `doctor` checks Python package import, settings load, and optional dependency
  URLs if configured.
- `config` prints sanitized config only.

## MCP Shell

Create a placeholder MCP server module with tool registration structure for
future tools:

- `retrieve_context`
- `get_related_work`
- `check_context_gate`
- `propose_canonical_decision`
- `approve_canonical_decision`

Phase 0 tools can return "not implemented" structured responses. The point is
to lock tool names and smoke-test import/registration shape.

## Docker Compose

Compose services:

- `api`
- `worker`
- `postgres`
- `redpanda`
- `qdrant`
- `minio`
- `redis` optional/profiled

Rules:

- `docker compose up api worker postgres` should be enough for a basic smoke.
- Redpanda/Qdrant/MinIO may start locally but Phase 0 tests cannot require them.
- Do not require Kubernetes.

## Tests

Minimum Phase 0 test suite:

- contract enum value tests,
- pipeline envelope validation tests,
- forbidden payload key tests,
- FastAPI health endpoint tests,
- dev route disabled/enabled tests,
- settings load tests,
- CLI smoke tests,
- worker `noop` smoke test,
- MCP server import/registration smoke test,
- log redaction tests.

Commands:

```bash
ruff check .
ruff format --check .
mypy src
pytest
```

Docker validation:

```bash
docker compose config
docker compose up -d postgres
pytest tests/api tests/contracts
```

## Acceptance Criteria

Phase 0 is complete when:

- repo installs locally in editable mode,
- typecheck/lint/tests pass,
- API health endpoints work,
- CLI `doctor` works,
- worker `noop` works,
- MCP shell imports and exposes planned tool names,
- pipeline envelope and status enums match docs,
- dev workbench routes are safely gated,
- Docker Compose config is valid,
- no test requires real Slack/GitHub/Linear/model provider credentials.

## Risks

- Overbuilding table migrations too early. Avoid by adding only skeleton DB
  wiring in Phase 0.
- Letting placeholders look production-ready. Name incomplete adapters clearly.
- Import-time infrastructure coupling. All optional services must initialize
  lazily.
- Secret/content logging. Add redaction now before real data exists.

## Follow-Up Into Phase 1

Phase 1 should build on this skeleton by adding:

- fixture provider contracts,
- fixture seed/reset endpoints,
- pipeline run records,
- workbench UI,
- deterministic data through the real interfaces.

