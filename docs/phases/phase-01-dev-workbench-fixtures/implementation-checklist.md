# Phase 1 Implementation Checklist

## 1. Dev Workbench Service Layer

- Add `src/cortex/dev/`.
- Add a `DevWorkbenchService` that owns fixture state, runs, evidence packs, and
  eval results for an app instance.
- Store service instance on `app.state` or provide it through a small dependency
  helper.
- Keep `src/cortex/api/routes/dev.py` limited to HTTP request/response wiring.

Acceptance:

- App imports without enabling the workbench.
- Enabled app can resolve the service.
- Disabled app still does not mount `/dev/*`.

## 2. Deterministic Fixture Bundle

- Define fixture records for Slack, Linear, GitHub, repo docs, and diagram/OCR.
- Use stable IDs, content hashes, timestamps, canonical URLs, and citations.
- Include the full COR-123 story:
  - Slack Postgres-session decision,
  - Slack diagram OCR,
  - Linear COR-123,
  - Linear COR-119 blocker,
  - GitHub PR 184,
  - stale Redis session doc.

Acceptance:

- `POST /dev/fixtures/seed` returns expected IDs.
- Seeding twice does not duplicate fixture records.
- `POST /dev/fixtures/reset` clears fixture state and run artifacts.

## 3. Pipeline Runner

- Add a deterministic runner for stages:
  - `seed`,
  - `ingest`,
  - `kafka_event`,
  - `normalize`,
  - `chunk_ocr`,
  - `embed`,
  - `index`,
  - `link`,
  - `retrieve`,
  - `gate`.
- Publish `PipelineEventEnvelope` records through `InMemoryEventBus`.
- Record stage status, timings, inputs, outputs, event IDs, trace IDs, and
  idempotency keys.

Acceptance:

- `POST /dev/pipeline/run` returns a `run_id`.
- `GET /dev/pipeline/runs/{run_id}` returns ordered stage records.
- Repeated runs produce deterministic artifact IDs.

## 4. Deterministic Retrieval Inspector

- Implement `POST /dev/retrieval/query`.
- Return query plan, filters, lexical candidates, vector candidates,
  relationship expansions, merged candidates, final ranking, and exclusions.
- Make the COR-123 query return every expected evidence source.

Acceptance:

- COR-123 retrieval includes Slack, diagram OCR, Linear, GitHub, and repo-doc
  evidence.
- Inspector output is stable across runs.

## 5. Evidence Pack And Gate

- Build a deterministic evidence pack for COR-123.
- Include claims, citations, source coverage, stale evidence, conflict summary,
  token budget, missing context, and permission exclusions placeholder.
- Evaluate the context gate as `block` for the stale Redis versus Postgres
  session conflict.

Acceptance:

- `GET /dev/evidence-packs/{id}` returns evidence JSON.
- Every citation resolves to a seeded source object or file.
- Gate result includes reason and required human action.

## 6. Workbench UI

- Replace placeholder `GET /dev/workbench` with server-rendered HTML.
- Show:
  - fixture state,
  - latest run status,
  - stage timeline,
  - retrieval inspector summary,
  - evidence pack summary,
  - gate status,
  - eval metrics.
- Render empty, seeded, running, failed, and complete states.

Acceptance:

- Workbench page renders when enabled.
- Workbench shows clear empty state before seeding.
- Failed stages render structured error details instead of blank output.

## 7. Eval Runner

- Implement `POST /dev/evals/run`.
- Include at least the COR-123 golden query.
- Report Recall@K, MRR, citation accuracy, conflict detection, gate accuracy,
  and latency.

Acceptance:

- Eval metrics are deterministic.
- COR-123 passes expected recall, citation, conflict, and gate checks.

## 8. Tests And Docs

- Add focused tests listed in [`test-plan.md`](test-plan.md).
- Update root README only if new local commands or env notes are required.
- Keep phase docs current when implementation choices change.

Acceptance:

- `ruff check .` passes.
- `ruff format --check .` passes.
- `mypy src` passes.
- `pytest` passes.

## Completion Criteria

Phase 1 is complete when:

- all acceptance checks above pass,
- every `/dev/*` endpoint is guarded,
- the workbench visually proves the COR-123 reduced loop,
- no real provider credentials or external services are required,
- later phases can replace deterministic implementations without changing the
  workbench route contract.

