# Phase 0 Autoplan Review

## Review Scope

Plan reviewed:

- [`plan.md`](plan.md)
- [`../implementation-roadmap.md`](../implementation-roadmap.md#phase-0-production-skeleton)
- [`../../architecture/v1-entity-state-schema.md`](../../architecture/v1-entity-state-schema.md)
- [`../../architecture/pipeline-event-envelope.md`](../../architecture/pipeline-event-envelope.md)

Autoplan mode:

- CEO review: scope and sequencing.
- Design review: skipped; Phase 0 has no customer UI scope.
- Engineering review: architecture, code organization, tests, failure modes.
- DX review: developer setup, commands, time-to-first-green-test.

## Executive Verdict

Phase 0 is approved for implementation after adding the companion checklist and
test plan in this directory.

The plan is appropriately scoped. It creates the production-shaped spine without
trying to build real ingestion, retrieval, or connectors. The biggest risk is
overbuilding database/domain behavior in Phase 0 instead of stopping at skeleton
contracts and smoke-testable interfaces.

## CEO Review

Score: 8/10.

What is right:

- The phase is infrastructure-first but not platform-heavy.
- It keeps the first value loop unblocked: Phase 1 fixtures and Phase 2 raw
  events can build directly on it.
- It explicitly avoids Slack OAuth, real retrieval, production auth, and
  Kubernetes.

Scope corrections:

- Keep Docker Compose in Phase 0, but do not require all services for unit
  tests.
- Keep DB migrations minimal. Do not create every production table before the
  raw-event and source-object phases need them.
- Keep MCP as shell/tool registration only. Do not implement retrieval tool
  behavior yet.

Auto-decisions:

| Decision | Classification | Choice | Rationale |
| --- | --- | --- | --- |
| DB schema depth | Scope | Minimal migration shell | Full domain schema now would freeze details too early. |
| Docker dependency | Scope | Compose available, tests mostly dependency-free | Local infra matters, but Phase 0 must run fast in CI/local. |
| MCP scope | Scope | Tool names + not-implemented responses | Locks integration surface without fake product behavior. |

## Engineering Review

Score: 8/10.

Findings:

1. The plan should distinguish Pydantic contracts from SQLAlchemy models.
   Decision: keep Pydantic contract stubs broad in Phase 0, keep SQLAlchemy
   domain tables minimal until Phase 2+.
2. The event bus interface should have an in-memory implementation now.
   Decision: implement `InMemoryEventBus`; keep Kafka implementation guarded or
   placeholder-only.
3. The dev guard should be tested before any dev workbench implementation.
   Decision: add explicit disabled/enabled tests for `/dev/*`.
4. The config model must avoid import-time connections.
   Decision: settings load only parses env; service clients initialize lazily.
5. Redaction should exist before real data.
   Decision: include log redaction helper and tests in Phase 0.

Required architecture diagram for implementation docs/code comments:

```txt
FastAPI app / CLI / worker / MCP shell
  -> Settings
  -> Contracts
  -> Interfaces
      -> EventBus
      -> ObjectStorage
      -> VectorIndex
      -> Cache / RateLimiter / Scheduler
  -> Observability
  -> DB session factory
```

Do not wire future services directly to concrete vendors in Phase 0.

## Test Review

Score: 8/10 after adding [`test-plan.md`](test-plan.md).

Critical coverage:

- contract enum exact values,
- pipeline envelope validation and forbidden payload keys,
- config default loading,
- FastAPI health endpoints,
- dev route disabled/enabled behavior,
- CLI smoke,
- worker `noop` smoke,
- MCP registration smoke,
- redaction helper.

No E2E browser tests are required in Phase 0. No model-provider evals are
required in Phase 0.

## Performance Review

Score: 7/10.

Performance risks are low because Phase 0 does not process real data. The main
performance concern is accidental slow startup from eager infrastructure
connections.

Decision:

- all external clients must be lazy,
- tests should import `cortex` without requiring Postgres, Kafka, Qdrant, MinIO,
  Redis, or model API keys.

## DX Review

Score: 8/10 after adding [`implementation-checklist.md`](implementation-checklist.md).

Target developer experience:

```txt
clone repo
  -> install dependencies
  -> run lint/typecheck/tests
  -> run API health locally
  -> run worker noop
  -> run CLI doctor
```

Target time to first green test: under 10 minutes on a prepared machine.

Required docs in implementation:

- `README.md` quickstart,
- `.env.example`,
- command list,
- Docker Compose notes,
- "what is intentionally not implemented yet" section.

## Final Gate

Approved implementation target:

```txt
Phase 0 = skeleton + contracts + interfaces + tests + local infra wiring.
```

Explicitly rejected for Phase 0:

```txt
real connectors
real Kafka consumers
real retrieval/ranking
full production DB schema
auth/session implementation
admin UI
Kubernetes manifests
Temporal workflows
Redis as required dependency
```

## Decision Audit Trail

| # | Area | Decision | Status |
| ---: | --- | --- | --- |
| 1 | Scope | Keep Phase 0 skeleton-only | Accepted |
| 2 | DB | Minimal Alembic shell, no full domain schema | Accepted |
| 3 | Events | In-memory event bus now, Kafka real implementation later | Accepted |
| 4 | API | Health endpoints and dev guard only | Accepted |
| 5 | MCP | Register tool names, return structured not-implemented | Accepted |
| 6 | Infra | Compose includes dependencies, tests do not require all of them | Accepted |
| 7 | Observability | Logging/tracing/redaction hooks now | Accepted |
| 8 | DX | README/.env/doctor/noop worker required | Accepted |

