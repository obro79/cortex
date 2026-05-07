# Phase 1 Autoplan Review

## Review Scope

Plan reviewed:

- [`plan.md`](plan.md)
- [`../implementation-roadmap.md`](../implementation-roadmap.md#phase-1-dev-workbench-and-deterministic-fixtures)
- [`../../product-plan.md`](../../product-plan.md)
- [`../../architecture/adrs/017-dev-workbench-deterministic-fixtures/README.md`](../../architecture/adrs/017-dev-workbench-deterministic-fixtures/README.md)
- Phase 0 code in `src/cortex/api`, `src/cortex/contracts`, and
  `src/cortex/events`.

Autoplan mode:

- CEO review: scope, wedge value, sequencing, and non-goals.
- Design review: run because Phase 1 includes `GET /dev/workbench`.
- Engineering review: architecture, contracts, test coverage, edge cases, and
  failure modes.
- DX review: run because this is a developer-facing internal tool and API.

Dual voice status:

- Codex CLI: installed, but auth probing is unavailable in this environment.
- Claude-style subagents: unavailable under this Codex session policy.
- Degradation: single-reviewer mode. Findings below are from local repo review
  and gstack autoplan methodology.

## Executive Verdict

Phase 1 is approved for implementation with one correction: the dev workbench
must be a deterministic harness over Phase 0 contracts and interfaces, not an
early production implementation of Phase 2-5 storage, indexing, and retrieval.

The plan should optimize for a truthful visual trace of the reduced v1 loop. It
should not fake a pretty demo state that does not exercise contract objects,
event envelopes, idempotency keys, citations, and gate behavior.

## Phase 1: CEO Review

Score: 8/10.

### Premise Challenge

| Premise | Verdict | Reasoning |
| --- | --- | --- |
| A deterministic fixture loop can validate the first Cortex wedge before live connectors. | Accepted | The product risk is missed or conflicting engineering context, and the COR-123 fixture directly tests that. |
| A dev UI is worth building before a customer UI. | Accepted | The pipeline has many stages. Developers need visual traceability before real source data exists. |
| Phase 1 should show the full reduced loop even though later phases own durable stages. | Accepted with constraint | The loop should be contract-true and deterministic, but in-process/local. |
| COR-123 is the right first story. | Accepted | It exercises Slack decisions, diagrams/OCR, Linear, GitHub, stale docs, retrieval, and gate blocking. |

### Existing Code Leverage Map

| Sub-problem | Existing code to reuse |
| --- | --- |
| Dev route guard | `src/cortex/api/app.py` and `tests/api/test_dev_guard.py` |
| Workbench route | `src/cortex/api/routes/dev.py` placeholder |
| Feature flag | `Settings.cortex_dev_workbench_enabled` |
| Entity shapes | `RawEvent`, `SourceObject`, `SourceFile`, `SourceChunk`, `EmbeddingRecord`, `RetrievalRequest`, `EvidencePack`, `ContextGateResult` |
| Pipeline events | `PipelineEventEnvelope` with causation, trace, versions, hashes, and forbidden payload key validation |
| In-memory publication | `InMemoryEventBus` |
| Local testing pattern | existing `tests/api`, `tests/contracts`, and `tests/smoke` layout |

### Dream State Mapping

```txt
CURRENT
  Phase 0 skeleton, gated /dev placeholder, contracts, event envelope, tests.

THIS PLAN
  Deterministic COR-123 fixture loop, visual pipeline timeline, retrieval
  inspector, evidence pack viewer, gate result, eval metrics.

12-MONTH IDEAL
  Live connector data flows through the same stages, permissions are enforced,
  retrieval is hybrid, gate decisions are explainable, and approved canonical
  decisions become durable team memory.
```

Dream state delta:

- Phase 1 leaves production persistence, provider auth, real indexing, and
  permission enforcement to later phases.
- Phase 1 should still lock the shape of the debug surface that later phases
  keep using.

### Implementation Alternatives

| Approach | Effort | Pros | Cons | Decision |
| --- | --- | --- | --- | --- |
| Hardcoded fake UI state | Low | Fastest visible demo | Does not validate contracts, events, or citations | Rejected |
| CLI-only fixture runner | Medium | Smaller UI scope | Fails ADR-017 visual trace requirement | Rejected |
| In-process deterministic harness over real contracts | Medium | Exercises real boundaries without premature infra | Requires careful scope discipline | Accepted |
| Build real Phase 2-5 stack now | High | Closer to production | Blows up phase scope and freezes details too early | Rejected |

### Temporal Interrogation

Hour 1:

- The developer should be able to seed fixtures and see stable IDs.
- If the dev flag is off, every `/dev/*` route should still be absent.

Hour 6:

- The developer should run COR-123 and inspect a stage-by-stage timeline.
- Failures should name the stage, run ID, trace ID, and fix.

Day 2:

- The team should have enough visual evidence to trust Phase 2 raw event work.
- New fixture cases should be easy to add without rewriting the workbench.

### Scope Decisions

| Decision | Classification | Result | Principle |
| --- | --- | --- | --- |
| Use in-process local state for Phase 1 artifacts. | Mechanical | Accepted | Explicit over clever |
| Keep real database tables for later phases. | Mechanical | Accepted | Phase boundary discipline |
| Build the workbench UI now. | Mechanical | Accepted | ADR-017 requires visual trace |
| Include deterministic eval metrics now. | Mechanical | Accepted | Completeness |
| Avoid real provider credentials and OAuth. | Mechanical | Accepted | Scope control |

## CEO Review Sections

### 1. Architecture Review

Examined the Phase 0 app factory, dev router, settings, entity contracts, and
pipeline envelope. The architecture is sound if Phase 1 adds a `cortex.dev`
service layer and keeps the API router thin. Directly building all behavior in
`routes/dev.py` would become hard to test and hard to reuse when later phases
replace in-memory stages with durable services.

### 2. Error And Rescue Map

| Failure | User sees | Rescue behavior |
| --- | --- | --- |
| Workbench disabled | `/dev/*` returns 404 | Enable `CORTEX_DEV_WORKBENCH_ENABLED=true` locally. |
| Fixtures not seeded | Empty workbench state | Show seed action and return `fixtures_not_seeded` from run/query endpoints. |
| Stage fails | Timeline marks failed stage | Include stage, run ID, trace ID, and actionable fix text. |
| Evidence pack missing | Evidence viewer returns 404 | List known evidence pack IDs from latest run. |
| Eval case fails | Eval panel shows failed case | Preserve per-case failure reason and metric summary. |

### 3. Security And Threat Model

The critical risk is accidentally exposing `/dev/*` in production. Preserve the
existing route registration guard and add disabled/enabled tests for every new
endpoint. Do not place raw content, OAuth tokens, secrets, embeddings, or OCR
text inside `PipelineEventEnvelope.payload`; the existing forbidden-key
validator should remain part of coverage.

### 4. Data Flow And Interaction Edge Cases

Seed, run, query, evidence-pack read, and eval run must work independently but
share the same in-memory dev state. Reset must clear only dev state. Repeated
seed and repeated pipeline runs should not create duplicate fixture artifacts.

### 5. Code Quality Review

The plan should keep fixture definitions declarative and deterministic. Avoid a
single large route file. Prefer small modules with obvious responsibilities:
fixtures, pipeline, retrieval, evidence, evals, and workbench rendering.

### 6. Test Review

The test plan must cover route guards, fixture idempotency, pipeline timeline,
retrieval output, evidence pack content, gate status, eval metrics, and HTML
rendering. Browser tests are not required yet because the UI can be
server-rendered and low-interaction.

### 7. Performance Review

Phase 1 data volume is tiny. Performance risk is mostly accidental startup or
state leakage. Keep all behavior lazy and in-process, and do not require
Postgres, Kafka, Qdrant, MinIO, Redis, or provider API keys for tests.

### 8. Observability And Debuggability Review

The run timeline is the observability surface. Every stage should expose trace
IDs, event IDs, input IDs, output IDs, status, and error details. This makes the
workbench useful before OpenTelemetry traces become meaningful in later phases.

### 9. Deployment And Rollout Review

No production rollout is required. The only rollout gate is config: local
developers opt in with `CORTEX_DEV_WORKBENCH_ENABLED=true`. Production and test
defaults remain disabled unless a test explicitly constructs enabled settings.

### 10. Long-Term Trajectory Review

This plan is aligned with the roadmap if the harness is built on contract
objects and does not hardcode UI-only data structures. The workbench should
survive later phases as the same diagnostic surface over increasingly real
services.

### 11. Design And UX Review

UI scope is internal and diagnostic. The workbench should be information-dense:
fixture state, latest run, stage timeline, retrieval inspector, evidence pack,
gate result, and eval metrics. Avoid a marketing-style page.

## Phase 2: Design Review

Score: 8/10.

| Dimension | Score | Finding | Decision |
| --- | ---: | --- | --- |
| Information architecture | 8 | First screen must show current state and latest gate result. | Accepted |
| Interaction states | 8 | Need empty, seeded, running, failed, and complete states. | Accepted |
| User journey | 8 | Developer should seed, run, query, inspect, and eval without leaving the page. | Accepted |
| Specificity | 7 | Plan now names concrete panels and fields. | Accepted |
| Design system alignment | 7 | No design system exists; use restrained FastAPI devtool HTML. | Accepted |
| Responsive/accessibility | 7 | Desktop-first is fine, but content must remain readable on narrow screens. | Accepted |
| Unresolved design decisions | 8 | No blocking taste decisions. | Accepted |

Design litmus scorecard:

```txt
1. What does the user see first? Fixture state, latest run, and gate status.
2. Can a failed run be diagnosed? Yes, via per-stage errors and trace IDs.
3. Are empty states specified? Yes, seed action and no-run state.
4. Is the UI specific? Yes, timeline, inspector, evidence, eval panels.
5. Will this haunt implementation? Low risk if the route stays thin.
```

## Phase 3: Engineering Review

Score: 8/10.

### Architecture Diagram

```txt
tests/api/test_dev_endpoints.py
  -> create_app(Settings(cortex_dev_workbench_enabled=True))
      -> /dev router
          -> DevWorkbenchService
              -> FixtureRepository
              -> FixturePipelineRunner
                  -> InMemoryEventBus
                  -> PipelineEventEnvelope
              -> DeterministicRetriever
              -> EvidencePackBuilder
              -> ContextGateEvaluator
              -> EvalRunner
```

### Engineering Findings

1. Route file size can become a problem.
   Decision: keep `src/cortex/api/routes/dev.py` as HTTP wiring only and put
   behavior under `src/cortex/dev`.
2. Real production stages are not ready.
   Decision: use deterministic in-memory artifacts typed to existing contracts,
   then replace implementations in later phases.
3. Idempotency can be hand-waved in a fixture harness.
   Decision: make seed IDs and stage output IDs deterministic and test repeats.
4. Evidence citations can drift from source objects.
   Decision: tests must assert every citation resolves to a seeded object/file.

### Test Diagram

```txt
Dev route guard
  -> each /dev endpoint disabled returns 404
  -> each /dev endpoint enabled is reachable

Fixture lifecycle
  -> reset clears state
  -> seed creates stable fixture IDs
  -> seed twice does not duplicate records

Pipeline run
  -> every stage appears in order
  -> envelopes include trace and causation fields
  -> repeated run remains deterministic

Retrieval
  -> COR-123 returns Slack, diagram OCR, Linear, GitHub, and repo-doc evidence
  -> inspector includes lexical, vector, relationship, merged, final ranking

Evidence and gate
  -> citations resolve
  -> stale Redis doc is marked stale/conflicting
  -> gate returns block with required human action

Evals
  -> Recall@K, MRR, citation accuracy, conflict detection, gate accuracy, latency
```

### Performance Review

No production performance issue is expected. Keep fixture state small and avoid
network calls. The latency metric in evals should measure local deterministic
execution only and should not become a hard performance promise.

## Phase 3.5: DX Review

Score: 8/10.

Developer persona:

- Cortex contributor implementing or debugging pipeline behavior locally.
- Needs fast proof that seed, run, retrieve, cite, gate, and eval are coherent.

Developer journey map:

| Stage | Desired experience |
| --- | --- |
| Discover | README links Phase 1 plan and quick dev flag. |
| Enable | Set `CORTEX_DEV_WORKBENCH_ENABLED=true`. |
| Start | Run FastAPI locally. |
| Seed | Click or call seed endpoint. |
| Run | Trigger pipeline run. |
| Inspect | Read timeline, IDs, and artifacts. |
| Query | Run COR-123 retrieval. |
| Evaluate | Run eval panel and metrics. |
| Debug | Use stage errors, trace IDs, and citations. |

Target time to hello world: under 5 minutes on a prepared local environment.

DX implementation checklist:

- Add README note for enabling the dev workbench.
- Keep endpoint responses copy-pasteable JSON.
- Return actionable errors with problem, cause, fix.
- Make fixture IDs stable and documented.
- Keep tests runnable with plain `pytest`.

## NOT In Scope

- Real provider connectors.
- Real OAuth/token management.
- Durable production pipeline tables.
- Real Kafka consumers or publishers.
- Real Qdrant/vector index integration.
- Production retrieval ranker.
- Customer UI.
- Browser E2E tests.

These are already covered by later roadmap phases and should not be duplicated
in Phase 1.

## What Already Exists

- Feature flag and route guard.
- Placeholder workbench route.
- Pydantic entity contracts.
- Pipeline event envelope and payload safety checks.
- In-memory event bus.
- FastAPI test patterns.

## Failure Modes Registry

| Failure mode | Severity | Mitigation |
| --- | --- | --- |
| Dev routes exposed when disabled | Critical | Disabled/enabled tests for every `/dev/*` endpoint. |
| Fixture harness bypasses real contracts | High | Type artifacts to existing Pydantic contracts and envelope shape. |
| Seed creates duplicates | Medium | Stable IDs and idempotency tests. |
| Evidence citations break | High | Citation resolution tests. |
| Gate returns allow for conflicting fixture | High | Golden COR-123 gate test expects `block`. |
| Workbench blank on error | Medium | Render failed stage and structured error details. |

## Cross-Phase Themes

The same concern appears in CEO, engineering, and DX review: Phase 1 must be
truthful, not just visual. The harness is valuable only if it exercises the
contracts and traceability later phases will preserve.

## Deferred To TODOS.md

No new `TODOS.md` entries were added. Deferred work is already represented by
the existing roadmap phases: raw event persistence, source-object
normalization, indexing, retrieval, context gate, permissions, and real
connectors.

## Final Gate

Approved implementation target:

```txt
Phase 1 = deterministic dev workbench + fixture loop + visual trace + retrieval
inspector + evidence pack + block gate + eval metrics.
```

Explicitly rejected for Phase 1:

```txt
real provider auth
real provider APIs
real production persistence for pipeline stages
real Kafka/Qdrant integration
customer UI
permission enforcement beyond placeholders
```

## Decision Audit Trail

| # | Phase | Decision | Classification | Principle | Rationale | Rejected |
| ---: | --- | --- | --- | --- | --- | --- |
| 1 | CEO | Use in-process deterministic harness | Mechanical | Explicit over clever | Validates the reduced loop without preempting later infra phases. | Hardcoded fake UI, full production stack |
| 2 | CEO | Keep workbench UI in Phase 1 | Mechanical | Completeness | ADR-017 requires a visual trace for pipeline trust. | CLI-only runner |
| 3 | Eng | Put behavior under `src/cortex/dev` | Mechanical | Code quality | Keeps routes thin and tests focused. | Large route module |
| 4 | Eng | Test every new endpoint disabled/enabled | Mechanical | Safety | Prevents dev surface from leaking into production mode. | Only testing `/dev/workbench` |
| 5 | Eng | Require citation resolution tests | Mechanical | Completeness | Evidence packs are not trustworthy if citations drift. | Snapshot-only tests |
| 6 | DX | Target under 5 minutes to first workbench run | Mechanical | Developer empathy | The workbench is a local debugging tool and must be fast to try. | Multi-service local setup |

