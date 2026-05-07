# Phase 1 Test Plan

## Commands

```bash
ruff check .
ruff format --check .
mypy src
pytest
```

Focused local loop:

```bash
pytest tests/api/test_dev_guard.py tests/api/test_dev_endpoints.py tests/dev
```

## Coverage Map

```txt
Dev route guard
  -> all /dev endpoints absent when disabled
  -> all /dev endpoints available when enabled

Fixture lifecycle
  -> reset clears state
  -> seed creates expected stable IDs
  -> seed twice is idempotent

Pipeline run
  -> run returns run_id
  -> run record has all expected stages in order
  -> stage records include trace IDs, event IDs, inputs, outputs, and summaries
  -> pipeline envelopes reject forbidden payload keys

Retrieval inspector
  -> COR-123 query returns expected sources
  -> lexical, vector, relationship, merged, and final rankings are present
  -> output is deterministic across repeated runs

Evidence pack
  -> claims and citations are present
  -> every citation resolves
  -> stale Redis doc is marked stale/conflicting
  -> source coverage includes Slack, Linear, GitHub, repo docs, and diagram OCR

Context gate
  -> COR-123 fixture returns block
  -> block reason names the conflicting architecture context
  -> required human action is present

Workbench UI
  -> empty state renders before seed
  -> seeded state renders fixture IDs
  -> completed run renders timeline, evidence, gate, and eval sections
  -> failed stage renders structured error detail

Evals
  -> Recall@K is reported
  -> MRR is reported
  -> citation accuracy is reported
  -> conflict detection is reported
  -> gate accuracy is reported
  -> latency is reported
```

## Tests To Create

| Test file | Assertions |
| --- | --- |
| `tests/api/test_dev_guard.py` | Extend disabled/enabled coverage to every new `/dev/*` endpoint. |
| `tests/api/test_dev_endpoints.py` | HTTP behavior for seed, reset, run, run read, query, evidence, eval, and workbench. |
| `tests/dev/test_fixture_seed_reset.py` | Stable IDs, idempotent seed, reset clears dev state only. |
| `tests/dev/test_pipeline_run.py` | Stage order, event envelopes, trace IDs, idempotency keys, repeated run determinism. |
| `tests/dev/test_retrieval_query.py` | COR-123 expected sources, inspector sections, deterministic ranking. |
| `tests/dev/test_evidence_pack.py` | Claims, citations, stale/conflict summary, source coverage, citation resolution. |
| `tests/dev/test_context_gate.py` | COR-123 returns `block` with reasons and required actions. |
| `tests/dev/test_evals.py` | Required metrics are present and expected golden case passes. |
| `tests/dev/test_workbench.py` | HTML renders empty, seeded, completed, and failed states. |

## Golden COR-123 Assertions

Minimum expected evidence:

- Slack decision thread approving Postgres sessions.
- Slack diagram OCR for intended session flow.
- Linear `COR-123` task.
- Linear `COR-119` middleware fallback blocker.
- GitHub PR `184` for partial session write migration.
- Repo doc that still says Redis is the session source of truth.

Minimum expected gate:

```json
{
  "status": "block",
  "risk_category": "architecture_conflict"
}
```

The exact JSON can contain more detail, but those values must be stable.

## Not Required In Phase 1

- real Slack/GitHub/Linear connector tests,
- OAuth/token tests,
- real Kafka integration tests,
- real Qdrant vector search tests,
- browser E2E tests,
- model-provider evals,
- production permission filtering tests.

Those belong to later phases once real services exist.
