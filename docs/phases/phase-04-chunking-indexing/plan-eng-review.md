# Phase 4 Engineering Review

## Review Verdict

Status: approved with corrections already folded into the plan.

Scope challenge result: proceed as-is. Phase 4 has several moving pieces, but
chunking, embeddings, and indexing are one derived-searchability boundary. The
scope is acceptable because retrieval/ranking remains deferred.

## What Already Exists

| Sub-problem | Existing code/docs | Reuse verdict |
| --- | --- | --- |
| Chunk/embedding/index contracts | `src/cortex/contracts/entities.py` | Reuse DTOs; add DB records and mapper tests. |
| Vector adapter boundary | `src/cortex/interfaces/vector_index.py` | Reuse; add local/test implementation. |
| Source object/file inputs | Phase 3 plan | Consume normalized records, not raw payloads. |
| Event envelope | `src/cortex/contracts/pipeline_events.py` | Reuse for chunk/embedding/index events. |
| Retrieval config | ADR-005 config-and-tuning | Use as versioned defaults. |
| Versioned config file | `config/retrieval-v1.yaml` | Use through a typed loader; avoid hidden constants for chunking, embeddings, candidate retrieval, and ranking. |
| Fixture story | Phase 1/3 docs | Preserve COR-123 chunk and citation expectations. |

## NOT In Scope

- Retrieval API, ranking, evidence packs, and context gate.
- Real provider-backed embeddings.
- Mandatory live Qdrant tests.
- OpenSearch.
- Semantic extraction.
- Permission filtering beyond storing metadata needed later.

## Architecture Review

1. [P1] (confidence: 9/10) `plan.md` — chunk text and OCR text are customer
   content. The plan correctly stores chunk text only in Postgres source tables
   and keeps event/vector payloads content-free.

2. [P2] (confidence: 8/10) `plan.md` — FTS can become a hidden side effect if
   chunk upsert directly mutates indexes without job state. The plan includes
   `index_jobs` for FTS and vector writes.

3. [P2] (confidence: 8/10) `plan.md` — deterministic embeddings must still
   behave like real embeddings structurally. The plan stores provider/model/
   dimensions/version metadata and vector hashes.

4. [P2] (confidence: 7/10) `plan.md` — Qdrant payloads often accidentally carry
   source text for convenience. The plan restricts vector payloads to filterable
   metadata only.

## Code Quality Review

1. [P2] (confidence: 8/10) `implementation-checklist.md` — chunking config must
   be centralized. The plan avoids hidden magic constants by requiring versioned
   YAML config from ADR-005 plus a typed loader.

2. [P2] (confidence: 8/10) `implementation-checklist.md` — index idempotency is
   easy to get wrong. The checklist requires unique target/version operation
   constraints and duplicate no-op tests.

3. [P3] (confidence: 7/10) `implementation-checklist.md` — record-to-DTO mapper
   tests should be added for `SourceChunk`, `EmbeddingRecord`, and `IndexJob`
   once DB records exist.

## Test Review

Detected framework: Python, pytest, pytest-asyncio.

```txt
CODE PATHS                                            SEARCHABILITY FLOWS
[+] Chunking/config                                  [+] COR-123 fixture search base
  ├── [★★  PLANNED] YAML typed loader                   ├── [★★  PLANNED] Slack decision chunk
  ├── [★★  PLANNED] Slack chunks                        ├── [★★  PLANNED] diagram OCR chunk
  ├── [★★  PLANNED] Linear chunks                       ├── [★★  PLANNED] Linear blocker chunk
  ├── [★★  PLANNED] GitHub chunks                       └── [★★  PLANNED] stale repo doc chunk
  ├── [★★  PLANNED] repo doc chunks
  └── [★★  PLANNED] OCR chunks

[+] Embeddings                                       [+] Index writes
  ├── [★★  PLANNED] deterministic repeatability         ├── [★★  PLANNED] FTS upsert job
  ├── [★★  PLANNED] version change behavior             ├── [★★  PLANNED] vector upsert job
  └── [★★  PLANNED] no vector/input logs                └── [★★  PLANNED] stale/delete cleanup

[+] Events
  ├── [★★  PLANNED] source_chunk.upserted
  ├── [★★  PLANNED] embedding requested/completed
  ├── [★★  PLANNED] index requested/completed
  └── [GAP]        DB record-to-DTO mapper tests

COVERAGE: 24/25 paths planned (96%) | GAPS: 1
QUALITY: ★★★:0 ★★:24 ★:0
```

Missing test to add during implementation:

- mapper tests from DB records to `SourceChunk`, `EmbeddingRecord`, and
  `IndexJob` DTOs, including enum serialization and retry fields.

## Performance Review

1. [P2] (confidence: 8/10) FTS and vector writes should be batch-oriented.
   Per-chunk writes are acceptable for fixture tests but the service APIs should
   accept lists.

2. [P2] (confidence: 7/10) deterministic embeddings should avoid high
   dimensional vectors in tests. Pick a small fixed test dimension while keeping
   dimension metadata explicit.

3. [P3] (confidence: 7/10) FTS indexes should be scoped by workspace/status/
   version. The plan includes smoke tests for those filters.

## Failure Modes

| Codepath | Production failure | Planned handling | Gap |
| --- | --- | --- | --- |
| Chunking | Source object content changes but old chunks remain active. | Mark old chunks stale on content/version change. | No gap. |
| FTS | Search returns chunks from another workspace. | Workspace/status/version smoke tests. | No gap. |
| Embedding | Embedding version changes but records mix old vectors. | Versioned embedding records. | No gap. |
| Vector payload | Chunk text leaks to Qdrant payload. | Metadata-only payload tests. | No gap. |
| Index job | Duplicate index jobs create repeated writes. | Unique job constraints. | No gap. |
| Deletion/stale | Deleted chunks remain searchable. | Cleanup jobs required. | No gap if cleanup tests pass. |

No critical silent gap found.

## Diagrams To Keep

Add inline ASCII comments where useful:

- `src/cortex/chunking/service.py`: source object/file -> chunks -> events.
- `src/cortex/embeddings/service.py`: requested -> deterministic vector ->
  completed -> vector index job.
- `src/cortex/indexing/service.py`: index job -> FTS/vector adapter ->
  completed/retry.

## Parallelization Strategy

| Step | Modules touched | Depends on |
| --- | --- | --- |
| Persistence/migrations | `src/cortex/db`, `alembic`, `tests/*` | — |
| Chunking config/chunker | `src/cortex/chunking`, `tests/chunking` | Phase 3 DTOs |
| Chunk publishers | `src/cortex/chunking`, `src/cortex/events` | Chunk DTO shape |
| Embedding provider/service | `src/cortex/embeddings`, `tests/embeddings` | Chunk DTO shape |
| Vector adapter/index jobs | `src/cortex/indexing`, `src/cortex/interfaces`, `tests/indexing` | Embedding DTO shape |
| Dev pipeline integration | `src/cortex/dev`, `tests/dev` | Chunking + embedding + indexing |

Parallel lanes:

- Lane A: persistence/migrations.
- Lane B: chunking config/chunker.
- Lane C: embedding provider can start after chunk DTO shape is agreed.
- Lane D: indexing after A + C.
- Lane E: dev integration last.

Conflict flags: chunk publishers and chunking service both touch
`src/cortex/chunking`; keep interface decisions in one lane.

## Completion Summary

- Step 0: Scope Challenge — scope accepted as-is.
- Architecture Review: 4 issues reviewed, corrections folded in.
- Code Quality Review: 3 issues reviewed, 1 mapper-test reminder remains.
- Test Review: diagram produced, 1 gap identified.
- Performance Review: 3 issues found.
- NOT in scope: written.
- What already exists: written.
- TODOs: none added.
- Failure modes: 0 critical gaps.
- Outside voice: skipped.
- Parallelization: 5 lanes, 2 early parallel lanes, rest dependency-sequenced.
- Lake Score: 5/5 recommendations choose the complete option.
