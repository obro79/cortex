# Phase 5 Autoplan Review

## Review Scope

Plan reviewed:

- [`plan.md`](plan.md)
- [`implementation-checklist.md`](implementation-checklist.md)
- [`test-plan.md`](test-plan.md)
- [`../implementation-roadmap.md`](../implementation-roadmap.md#phase-5-retrieval-and-evidence-packs)
- retrieval/evidence schema,
- hybrid retrieval, source allowlist, and retrieval eval ADRs,
- [`../../../config/retrieval-v1.yaml`](../../../config/retrieval-v1.yaml).

Autoplan mode:

- CEO review: product wedge and phase boundary.
- Design review: skipped because Phase 5 has no UI.
- Engineering review: retrieval flow, permissions, ranking, evidence, tests.
- DX review: deterministic golden query workflow.

## Executive Verdict

Phase 5 is approved if it returns cited, permission-safe context and does not
start making gate decisions. The phase should prove that hybrid retrieval can
find the COR-123 evidence and package it compactly for agents.

## CEO Review

Score: 9/10.

| Premise | Verdict | Reasoning |
| --- | --- | --- |
| Retrieval must be task-specific and cited. | Accepted | This is the core product wedge versus broad memory dumps. |
| Source allowlist filtering must happen before ranking. | Accepted | Ranking non-allowlisted candidates risks leakage through debug output. |
| Gate decisions should wait until Phase 6. | Accepted | Evidence must be trustworthy before block/warn logic. |
| Compact text plus JSON is required. | Accepted | Agents need concise text; tools and UI need structured evidence. |

## Engineering Review

Score: 8/10.

```txt
MCP/API query
  -> RetrievalRequest
  -> FTS + vector + relationships
  -> allowlist filter
  -> rank/merge
  -> EvidencePack
  -> compact text + JSON
```

Key decisions:

1. Permissions before ranking.
   Decision: non-allowlisted chunks never reach ranking/evidence.
2. Retrieval config is source of truth.
   Decision: candidate, ranking, and token-budget values come from YAML.
3. Evidence packs are durable.
   Decision: store citations and summaries for gate/approval/audit.
4. No LLM reranking.
   Decision: deterministic ranking until evals prove need.
5. No gate status.
   Decision: Phase 6 consumes evidence packs and decides allow/warn/block.

## DX Review

Score: 8/10.

The local loop should be:

```txt
pytest tests/retrieval tests/mcp
pytest tests/retrieval/test_golden_cor_123.py
```

The plan is good if a developer can run the golden COR-123 query locally without
network calls and inspect candidate summaries when expected evidence is missing.

## Risks

| Risk | Mitigation |
| --- | --- |
| Permission leaks through candidate summaries. | Filter before ranking and test safe exclusion summaries. |
| Ranking hides stale/conflicting evidence. | Keep stale/conflict summaries visible in evidence pack fields. |
| Token budget drops critical evidence. | Drop lower-ranked evidence first and record omissions. |
| FTS/vector candidates diverge by version. | Filter current chunking/embedding versions. |
| MCP tools return gate-like language too early. | Tests assert no allow/warn/block status. |

## Final Approval Gate

Approved to implement if:

- evidence citations resolve,
- permission safety tests pass,
- golden COR-123 query returns all expected evidence,
- token budget tests pass,
- Phase 6 gate decisions stay out of Phase 5.
