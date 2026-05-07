# Phase 4 Autoplan Review

## Review Scope

Plan reviewed:

- [`plan.md`](plan.md)
- [`implementation-checklist.md`](implementation-checklist.md)
- [`test-plan.md`](test-plan.md)
- [`../implementation-roadmap.md`](../implementation-roadmap.md#phase-4-chunking-and-indexing-base)
- [`../../architecture/v1-entity-state-schema.md`](../../architecture/v1-entity-state-schema.md)
- [`../../architecture/pipeline-event-envelope.md`](../../architecture/pipeline-event-envelope.md)
- Retrieval/chunking/embedding ADRs.

Autoplan mode:

- CEO review: wedge value and phase boundary.
- Design review: skipped because Phase 4 has no UI.
- Engineering review: data model, derived index lifecycle, idempotency, tests.
- DX review: deterministic local searchability loop.

## Executive Verdict

Phase 4 is approved if it stays focused on making normalized fixture data
searchable, not retrieving/ranking it. The product value is to prove that the
COR-123 fixture sources produce stable cited chunks, deterministic embeddings,
and index jobs that Phase 5 can query.

## CEO Review

Score: 8/10.

| Premise | Verdict | Reasoning |
| --- | --- | --- |
| Source-aware chunking belongs before retrieval. | Accepted | Retrieval quality depends on chunk boundaries and citations. |
| Deterministic embeddings are enough for Phase 4. | Accepted | They make tests stable and avoid provider cost while preserving adapter shape. |
| Postgres FTS and vector adapter should both exist now. | Accepted | Phase 5 needs hybrid candidate paths. |
| Retrieval API should wait. | Accepted | Ranking/evidence/gate scope belongs to Phase 5+. |

Scope decisions:

- Add chunk/embedding/index persistence now.
- Add FTS smoke and local vector adapter now.
- Keep real embedding providers and real Qdrant optional.
- Keep retrieval/ranking/evidence out.

## Engineering Review

Score: 8/10.

```txt
source_object.upserted/source_file.fetched
  -> chunker
  -> source_chunks
  -> embedding records
  -> deterministic provider
  -> index jobs
  -> Postgres FTS + VectorIndex adapter
```

Key decisions:

1. Chunk text is content.
   Decision: store in Postgres for FTS/citations, but never log or include in
   event/vector payloads.
2. Indexes are derived.
   Decision: Postgres source tables own state; FTS/vector writes are rebuildable.
3. Versioning controls rebuilds.
   Decision: `config/retrieval-v1.yaml` owns chunking and embedding versions
   that determine stale/rebuild behavior.
4. Deterministic provider prevents flaky tests.
   Decision: no network embedding calls in Phase 4.
5. Index jobs prevent hidden side effects.
   Decision: writes to FTS/vector paths are represented as idempotent jobs.

## DX Review

Score: 8/10.

The local loop should stay:

```txt
pytest tests/chunking tests/embeddings tests/indexing
alembic upgrade head
```

The plan is implementable if the local vector adapter and deterministic
embedding provider make all core tests run without external services.

## Risks

| Risk | Mitigation |
| --- | --- |
| Chunk boundaries miss key evidence. | Source-aware fixture snapshot tests and citations. |
| Chunk text leaks to logs/events/vector payloads. | Forbidden payload and logging tests. |
| Embedding version changes mix incompatible vectors. | Unique embedding version metadata and rebuild tests. |
| Index jobs duplicate writes. | Unique target/version operation constraints. |
| FTS queries accidentally cross tenants. | Workspace/status/version scoped smoke tests. |

## Final Approval Gate

Approved to implement if:

- Phase 4 emits stable cited chunks from Phase 3 records,
- deterministic embeddings are repeatable,
- FTS/vector index paths are adapter-backed and rebuildable,
- no retrieval/ranking/evidence scope enters this phase,
- content-bearing data stays out of events, vector payloads, and logs.
