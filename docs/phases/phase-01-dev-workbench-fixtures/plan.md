# Phase 1 Plan: Dev Workbench And Deterministic Fixtures

## Goal

Build a dev-only workbench that lets Cortex developers visually exercise the
first reduced v1 loop before real connectors exist.

The workbench must prove the "COR-123" demo path end to end with deterministic
fixtures:

```txt
fixture seed
  -> provider-shaped raw events
  -> pipeline timeline events
  -> normalized source objects and files
  -> chunks and OCR text
  -> deterministic embeddings and index candidates
  -> relationships
  -> retrieval inspector
  -> evidence pack
  -> context gate result
```

This phase should use the Phase 0 FastAPI app, `/dev/*` guard, Pydantic
contracts, `PipelineEventEnvelope`, and local interfaces. It should not create
the real production data pipeline early. Phase 2 still owns durable raw event
persistence. Phase 3 owns production source-object normalization. Phase 4 owns
real indexing. Phase 5 owns production retrieval and evidence packs.

## Inputs

- [`../implementation-roadmap.md`](../implementation-roadmap.md#phase-1-dev-workbench-and-deterministic-fixtures)
- [`../../product-plan.md`](../../product-plan.md)
- [`../../architecture/adrs/017-dev-workbench-deterministic-fixtures/README.md`](../../architecture/adrs/017-dev-workbench-deterministic-fixtures/README.md)
- [`../phase-00-production-skeleton/plan.md`](../phase-00-production-skeleton/plan.md)

## Existing Foundation

Phase 0 already provides:

- `src/cortex/api/app.py`: FastAPI app factory and gated dev router mounting.
- `src/cortex/api/routes/dev.py`: placeholder `GET /dev/workbench`.
- `src/cortex/config.py`: `CORTEX_DEV_WORKBENCH_ENABLED` flag.
- `src/cortex/contracts/entities.py`: broad Pydantic entity contracts for raw
  events, source objects, chunks, embeddings, retrieval requests, evidence packs,
  and gate results.
- `src/cortex/contracts/pipeline_events.py`: content-safe
  `PipelineEventEnvelope`.
- `src/cortex/events/in_memory.py`: in-memory event bus for tests.
- `tests/api/test_dev_guard.py`: disabled/enabled `/dev/workbench` guard tests.

## Product Story

The deterministic fixture bundle models the first wow demo:

```txt
Task: "I am implementing Linear issue COR-123. What prior decisions constrain
this work, and is any context stale or conflicting?"
```

Seeded evidence:

- Slack thread approving Postgres sessions.
- Slack diagram file with OCR text describing the intended Postgres session
  flow.
- Linear `COR-123` session migration task.
- Linear blocker issue for middleware fallback.
- GitHub PR partially migrating session writes.
- Repo doc that still says Redis is the session source of truth.

Expected result:

- Retrieval returns every seeded source with stable citations.
- The retrieval inspector shows why each candidate was selected and ranked.
- The evidence pack reports a conflict between stale Redis docs and newer
  Postgres-session evidence.
- The context gate returns `block` with required human action.

## Non-Goals

- No real Slack, Linear, GitHub, repo-doc connector calls.
- No OAuth, provider tokens, source selection, or webhook handling.
- No durable `raw_events`, `source_objects`, chunk, embedding, or relationship
  tables.
- No real Kafka/Redpanda publication requirement.
- No real Qdrant vector search requirement.
- No production retrieval ranker.
- No customer-facing UI or auth system.
- No LLM/provider-backed OCR or semantic extraction.

## Architecture

```txt
FastAPI app
  -> gated /dev router
      -> DevWorkbenchService
          -> FixtureRepository
          -> FixturePipelineRunner
          -> DeterministicRetriever
          -> EvidencePackBuilder
          -> ContextGateEvaluator
          -> EvalRunner
      -> InMemoryEventBus
      -> Pydantic contracts and PipelineEventEnvelope
```

The service can be in-process and local-only. The important constraint is that
each stage uses the same contract names and event envelope shape that later
production stages will use.

## Proposed Module Layout

```txt
src/cortex/dev/
  __init__.py
  fixtures.py
  pipeline.py
  retrieval.py
  evidence.py
  evals.py
  workbench.py

tests/dev/
  test_fixture_seed_reset.py
  test_pipeline_run.py
  test_retrieval_query.py
  test_evidence_pack.py
  test_evals.py

tests/api/
  test_dev_guard.py
  test_dev_endpoints.py
```

The existing `src/cortex/api/routes/dev.py` should stay thin and delegate to
`src/cortex/dev/*`.

## Dev Endpoints

| Endpoint | Behavior |
| --- | --- |
| `GET /dev/workbench` | Returns a server-rendered internal workbench page when enabled. |
| `POST /dev/fixtures/reset` | Clears in-memory fixture state, run records, event log, and evidence packs. |
| `POST /dev/fixtures/seed` | Seeds the deterministic COR-123 fixture bundle and returns created IDs. |
| `POST /dev/pipeline/run` | Runs the deterministic fixture pipeline and returns a `run_id`. |
| `GET /dev/pipeline/runs/{run_id}` | Returns run status, stage timeline, envelope IDs, trace IDs, and artifacts. |
| `POST /dev/retrieval/query` | Runs deterministic retrieval for a query and returns inspector details. |
| `GET /dev/evidence-packs/{id}` | Returns the evidence pack JSON plus citation and gate summaries. |
| `POST /dev/evals/run` | Runs deterministic eval cases and returns metric summaries. |

All endpoints must remain unavailable when
`CORTEX_DEV_WORKBENCH_ENABLED=false`.

## Fixture Data Contract

Use deterministic IDs and content hashes. Avoid hidden randomness in seeded
objects.

Minimum fixture records:

| Fixture | Stable ID | Purpose |
| --- | --- | --- |
| Slack decision thread | `slack-thread-sessions-postgres` | Newer decision evidence. |
| Slack diagram file | `slack-file-session-flow-diagram` | OCR and diagram evidence. |
| Linear task | `linear-issue-COR-123` | User task anchor. |
| Linear blocker | `linear-issue-COR-119` | Required rollout caveat. |
| GitHub PR | `github-pr-184` | Partial implementation evidence. |
| Repo doc | `repo-doc-session-storage` | Stale Redis conflict. |

Each fixture should produce:

- provider-shaped raw input,
- one or more source objects,
- source files when relevant,
- source chunks,
- deterministic embedding/vector metadata,
- relationship edges,
- citations resolvable back to source objects or files.

## Pipeline Timeline

The workbench should render these stages in order:

```txt
seed
  -> ingest
  -> kafka_event
  -> normalize
  -> chunk_ocr
  -> embed
  -> index
  -> link
  -> retrieve
  -> gate
```

Each stage record should include:

- stage name,
- status,
- started/completed timestamps,
- input IDs,
- output IDs,
- pipeline event IDs,
- trace ID,
- idempotency key,
- human-readable summary,
- error object when failed.

## Retrieval Inspector

`POST /dev/retrieval/query` should return:

- normalized query,
- filters,
- full-text candidates,
- vector candidates,
- relationship expansions,
- merged candidate list,
- final ranking,
- excluded candidates,
- generated evidence pack ID,
- gate status.

For Phase 1, lexical/vector scoring may be deterministic and simple. It still
needs to expose the same fields that a future real retriever will populate.

## Evidence Pack Viewer

The evidence pack should include:

- claims,
- citations,
- stale evidence,
- conflicting evidence,
- source coverage,
- token budget,
- missing context,
- permission exclusions placeholder,
- gate result.

The viewer can be server-rendered HTML backed by JSON endpoints. It should be a
working devtool, not a decorative mock. The first screen should show current
fixture state, latest run status, key metrics, and the current gate outcome.

## Eval Panel

`POST /dev/evals/run` should compute deterministic metrics:

- Recall@K,
- MRR,
- citation accuracy,
- conflict detection,
- gate accuracy,
- latency.

The minimum eval case is the COR-123 query. Add data structures that let later
phases add more fixture queries without rewriting the endpoint.

## Idempotency And Traceability

Seed/reset/run behavior must be predictable:

- Re-seeding the same bundle should not duplicate fixture records.
- Duplicate stage execution should no-op or update the same deterministic output
  IDs where applicable.
- Pipeline events should carry stable causation fields.
- Every output surfaced in the workbench should be traceable to a run ID and
  fixture ID.
- Reset should clear only dev fixture state, never global app state.

## Error Handling

Return structured errors with:

- `code`,
- `message`,
- `stage`,
- `run_id` when available,
- `trace_id` when available,
- actionable fix text.

The workbench should render failures inline in the timeline. A failed stage
should not produce a blank page.

## Security And Safety

- Keep dev routes registered only when `CORTEX_DEV_WORKBENCH_ENABLED=true`.
- Do not put real secrets, OAuth tokens, or raw provider payloads into event
  envelope payloads.
- Use synthetic fixture content only.
- Make the workbench visibly dev-only in the HTML title/header.
- Keep production mode behavior unchanged: `/dev/*` returns 404 or is absent.

## Implementation Sequence

1. Add `src/cortex/dev` service modules and an app-state factory.
2. Define deterministic fixture records and fixture repository behavior.
3. Implement seed/reset endpoints with guard tests.
4. Implement pipeline run records, stage timeline, and event publication through
   `InMemoryEventBus`.
5. Implement deterministic source objects, chunks, OCR text, embeddings,
   relationships, and evidence pack assembly.
6. Implement deterministic retrieval inspector and gate evaluator for COR-123.
7. Replace the placeholder workbench with a server-rendered dev UI.
8. Implement eval runner and metrics endpoint.
9. Add focused tests and update README commands if new commands are introduced.

## Acceptance Criteria

Phase 1 is complete when:

- all `/dev/*` endpoints are unavailable unless the dev workbench flag is true,
- fixture reset/seed endpoints create deterministic IDs and can be repeated,
- a pipeline run shows every planned stage with traceable outputs,
- the COR-123 query returns Slack, diagram OCR, Linear, GitHub, and repo-doc
  evidence with stable citations,
- stale Redis docs conflict with newer Postgres-session evidence,
- the context gate returns `block`,
- the eval endpoint reports the required metrics,
- the workbench page renders the current run, retrieval inspector, evidence
  pack, and eval summary,
- `ruff check .`, `ruff format --check .`, `mypy src`, and `pytest` pass.

## Main Risks

- The fixture harness could bypass service boundaries and give false confidence.
  Mitigation: keep contracts and envelope fields aligned with later phases.
- Deterministic scoring could overfit the COR-123 story. Mitigation: keep eval
  case definitions extensible.
- Dev routes could leak into production. Mitigation: preserve route registration
  guard and test every new endpoint disabled/enabled.
- UI scope could grow into a customer app. Mitigation: keep it an internal
  diagnostic workbench.

