# Phase 5 Implementation Checklist

## 1. Config And Contracts

- Extend `config/retrieval-v1.yaml` with token-budget defaults.
- Add/extend typed retrieval config loader for candidate retrieval, ranking, and
  token budgets.
- Ensure evidence packs record retrieval config, ranker, candidate, and token
  budget versions.

Acceptance:

- YAML defaults match ADR-005,
- invalid limits/weights/version fields fail validation,
- base ranking weights must sum to `1.0`; additive boosts validate separately,
- evidence pack records include the config versions that produced them.

## 2. Persistence

- Add `RetrievalRequestRecord` and `EvidencePackRecord`.
- Add migrations and indexes from `v1-entity-state-schema.md`.
- Add repositories for create, update status, complete, partial, failed,
  consumed, expired, and deleted states.

Acceptance:

- lifecycle transitions are enforced,
- query/snippet content is not logged,
- evidence pack expiry/status queries are index-backed.

## 3. Query Planner

- Parse task hints, issue IDs, PR numbers, file paths, provider filters, and
  source allowlist snapshots.
- Normalize query text for FTS/vector paths.
- Avoid logging raw query text.

Acceptance:

- COR-123 query extracts issue ID and task context,
- provider/source filters are deterministic,
- source allowlist snapshot hash is recorded.

## 4. Candidate Retrieval

- Implement Postgres FTS candidate retrieval.
- Implement VectorIndex candidate retrieval.
- Implement deterministic query embedding for dev/test.
- Implement relationship expansion from deterministic seeds.
- Apply workspace, status, chunking version, embedding version, provider/source,
  and source allowlist filters.

Acceptance:

- FTS candidates are workspace-scoped,
- vector candidates are workspace/source allowlist scoped,
- relationship expansion respects limits and allowlists,
- candidate limits come from config,
- single-path FTS/vector/relationship failures return safe partial results,
- all-path candidate failure marks the retrieval request failed.

## 5. Permission Filter

- Enforce source allowlist before candidates reach ranking or evidence packs.
- Redact non-allowlisted names, URLs, file names, snippets, chunk IDs, and debug
  IDs.
- Record safe exclusion counts/summaries only.

Acceptance:

- non-allowlisted chunks never appear in output,
- permission exclusions do not leak source identity,
- permission ambiguity returns partial/failed state for Phase 6 to fail closed.

## 6. Ranking And Merge

- Deduplicate FTS/vector/relationship candidates.
- Score candidates using config weights.
- Cap chunks per source object.
- Preserve score components in candidate summaries.

Acceptance:

- ranking tests are deterministic,
- exact identifiers like COR-123 and PR 184 rank correctly,
- stale docs can remain visible but lower-ranked/flagged when newer evidence
  exists.

## 7. Evidence Pack Builder

- Build claims, citations, source coverage, permission exclusions, missing
  context, stale context, conflict summary, and candidate summary.
- Resolve every citation to source chunk and source object/file.
- Apply token budget and snippet limits.
- Render compact agent text plus structured JSON.

Acceptance:

- max-token budget tests pass,
- citations always resolve,
- omitted evidence is recorded safely,
- no non-allowlisted content appears in evidence packs.

## 8. MCP Tools

- Implement `retrieve_context`.
- Implement `get_related_work`.
- Return `ok`, request/pack IDs, compact text, structured JSON, status, latency,
  and safe permission exclusion summary.

Acceptance:

- unknown args fail with structured errors,
- tool smoke tests pass,
- no Phase 6 gate status is returned.

## 9. Events And Evals

- Publish `evidence_pack.created` after durable pack creation.
- Add golden COR-123 retrieval eval.
- Track Recall@K, MRR, citation accuracy, permission safety, latency, and token
  count.

Acceptance:

- event envelope is pointer-only,
- golden query returns expected evidence,
- eval metrics are deterministic.

## Completion Criteria

Phase 5 is complete when:

- hybrid retrieval works over Phase 4 indexes,
- MCP tools return cited context,
- evidence packs are durable and permission-safe,
- golden query and ranking/token/citation tests pass,
- Phase 6 can consume evidence packs for allow/warn/block decisions.
