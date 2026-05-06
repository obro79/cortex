# ADR-017: Dev Workbench And Deterministic Pipeline Fixtures

## Status

Accepted.

## Decision

Build a dev-only visual workbench that uses deterministic fixture data to test
the real Cortex pipeline before live connectors are complete.

## What It Is

The dev workbench is an internal FastAPI UI and endpoint set under `/dev/*`.
It shows mock Slack, Linear, GitHub, repo docs, and diagram fixtures moving
through ingest, Kafka publication, raw storage, normalization, chunk/OCR,
embedding, indexing, linking, retrieval, context gate, and evidence-pack
generation.

## Why Cortex Uses It

- The architecture has many asynchronous stages that are hard to trust without a
  visual trace.
- Mock fixtures make retrieval quality and gate behavior repeatable.
- The workbench gives developers and design partners a fast way to see whether
  data was ingested, embedded, stored, and retrieved correctly.

## Required Fixture Story

The deterministic fixture bundle models the first wow demo:

- Slack thread approving Postgres sessions.
- Slack diagram file with OCR text for the intended session flow.
- Linear `COR-123` session migration task.
- Linear blocker issue for middleware fallback.
- GitHub PR partially migrating session writes.
- Repo doc still saying Redis is source of truth.

Expected retrieval result: all five evidence sources appear with citations and
the context gate returns `block`.

## Dev Endpoints

- `GET /dev/workbench`
- `POST /dev/fixtures/reset`
- `POST /dev/fixtures/seed`
- `POST /dev/pipeline/run`
- `GET /dev/pipeline/runs/{run_id}`
- `POST /dev/retrieval/query`
- `GET /dev/evidence-packs/{id}`
- `POST /dev/evals/run`

All endpoints are disabled unless `CORTEX_DEV_WORKBENCH_ENABLED=true`.

## Alternatives Considered

- Hardcoded fake UI states.
- CLI-only fixture testing.
- Live sandbox connectors immediately.

## Why Alternatives Lost

- Hardcoded UI does not validate architecture.
- CLI-only output does not satisfy the need to visually inspect the pipeline.
- Live sandbox connectors add credential and provider complexity too early.

## Tradeoffs

- Dev-only routes must be strongly guarded.
- Deterministic fixtures can overfit if they become the only eval data.
- The workbench adds UI/API scope before the customer UI.

## Failure Modes

- Workbench accidentally enabled in production.
- Fixture pipeline bypasses real service boundaries and gives false confidence.
- Deterministic embeddings hide quality problems with live embedding providers.

## How We Test It

- Dev guard tests prove `/dev/*` is unavailable unless explicitly enabled.
- Fixture seed tests verify expected raw events, source objects, chunks, files,
  embeddings, relationships, and evidence packs are created.
- Pipeline run tests prove each stage is idempotent and traceable.
- Retrieval tests verify the `COR-123` fixture returns the expected evidence and
  `block` gate result.

## How This Maps From CortexG

`cortexg` has deterministic seed data, retrieval evals, and demo surfaces.
Cortex turns that idea into a dev-only visual pipeline harness that exercises the
production-shaped Python service interfaces.

