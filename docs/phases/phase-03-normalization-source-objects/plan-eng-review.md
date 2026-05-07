# Phase 3 Engineering Review

## Review Verdict

Status: approved with the corrections already folded into the plan.

Scope challenge result: proceed as-is. Phase 3 necessarily touches
normalization, persistence, publication, fixtures, relationship seeds, and tests.
That is the complete source-object boundary and should not be split unless the
implementation PR becomes too large.

## What Already Exists

| Sub-problem | Existing code or docs | Reuse verdict |
| --- | --- | --- |
| Source object/file contracts | `src/cortex/contracts/entities.py` | Reuse as API DTOs; add DB records and mapping tests. |
| Raw event pointer loading | Phase 2 plan | Reuse `handle_raw_event_persisted` boundary. |
| Event envelope | `src/cortex/contracts/pipeline_events.py` | Reuse directly for source object/file events. |
| Fixture story | `src/cortex/dev/fixtures.py` | Reuse fixture payload builders, not in-memory normalized objects. |
| DB migration shell | `alembic/` and `src/cortex/db/models.py` | Extend narrowly with source object/file tables. |
| Dev workbench expectations | `tests/dev` | Keep as regression coverage for IDs/counts. |

## NOT In Scope

- Real provider API calls and OAuth.
- Generic production connector payload coverage.
- Chunking, OCR workers, embeddings, FTS, Qdrant, retrieval, and gate behavior.
- Full relationship graph service or ranking.
- Full Kafka consumer framework.
- Provider-native ACL enforcement.

## Architecture Review

1. [P1] (confidence: 9/10) `plan.md` — source text and OCR text are tempting to
   carry in `source_objects` or event payloads, but Phase 4 needs a clean
   boundary. The plan now persists fixture OCR text on `source_files` for later
   chunking while keeping event payloads and logs content-free.

2. [P2] (confidence: 8/10) `plan.md` — `source_files` is not fully specified in
   `v1-entity-state-schema.md`, but it is present in contracts and ADR-011.
   The plan now spells out the Phase 3 source file fields, including OCR text
   and hash, to avoid implementer guesswork.

3. [P2] (confidence: 8/10) `plan.md` — relationship work can become a graph
   project. The plan constrains Phase 3 to deterministic relationship seeds
   only.

4. [P2] (confidence: 7/10) `plan.md` — normalized version changes need to
   reprocess even when payload hash is unchanged. The plan now includes this as
   an idempotency rule.

## Code Quality Review

1. [P2] (confidence: 8/10) `implementation-checklist.md` — normalizers need a
   single result contract. The plan includes `NormalizationResult` so each
   provider does not invent its own output shape.

2. [P2] (confidence: 8/10) `implementation-checklist.md` — dev fixtures already
   create normalized objects in memory. Phase 3 must avoid building a second
   inconsistent path. The checklist says fixture normalizers use Phase 2 raw
   payload bytes as the source input.

3. [P3] (confidence: 7/10) `implementation-checklist.md` — source object record
   vs Pydantic DTO mapping can blur. Implementation should add mapper tests
   where repository records are converted to `SourceObject`/`SourceFile`.

## Test Review

Detected framework: Python, pytest, pytest-asyncio.

```txt
CODE PATHS                                            OPERATOR FLOWS
[+] Fixture normalizers                               [+] Replay raw event
  ├── [★★  PLANNED] Slack thread/message                 ├── [★★  PLANNED] unchanged no-op
  ├── [★★  PLANNED] Slack diagram file                   ├── [★★  PLANNED] content hash update
  ├── [★★  PLANNED] Linear issue                         └── [★★  PLANNED] normalized version update
  ├── [★★  PLANNED] GitHub PR
  └── [★★  PLANNED] repo doc section

[+] Persistence                                      [+] Publish downstream events
  ├── [★★  PLANNED] source object upsert                ├── [★★  PLANNED] source_object.upserted
  ├── [★★  PLANNED] source file upsert                  ├── [★★  PLANNED] source_file.fetched
  ├── [★★  PLANNED] OCR text/hash persistence           └── [★★  PLANNED] forbidden content rejection
  ├── [★★  PLANNED] relationship seed upsert
  └── [GAP]        record-to-DTO mapper tests

[+] Worker/service
  ├── [★★  PLANNED] load raw event by pointer
  ├── [★★  PLANNED] invalid payload retry/deadletter
  ├── [★★  PLANNED] durable write before publish
  └── [★★  PLANNED] publish failure retry state

COVERAGE: 22/23 paths planned (96%) | GAPS: 1
QUALITY: ★★★:0 ★★:22 ★:0
```

Missing test to add during implementation:

- mapper tests from `SourceObjectRecord`/`SourceFileRecord` to
  `SourceObject`/`SourceFile` DTOs, including enum serialization and metadata.

## Performance Review

1. [P2] (confidence: 7/10) normalization replay can generate a burst of
   downstream events. Keep no-op checks before publication and use batch-oriented
   upserts.

2. [P3] (confidence: 7/10) source object/content hash indexes are sufficient for
   fixture scale. Do not add search indexes or chunk tables in Phase 3.

## Failure Modes

| Codepath | Production failure | Planned handling | Gap |
| --- | --- | --- | --- |
| Raw event load | Missing raw event referenced by envelope. | Phase 2 retry/deadletter semantics. | No gap. |
| Payload parse | Fixture/provider shape invalid. | Structured error and retry/deadletter. | No gap. |
| Source object upsert | Unique identity race. | Unique index plus upsert tests. | No gap. |
| Source file metadata | Filename/OCR leaks to logs or event payload. | Hash filename, forbid content in envelopes/logs. | No gap if tests added. |
| Publish | Event bus publish fails after DB write. | Retryable raw event state. | No gap. |
| Replay | Unchanged source object republishes. | Content hash/normalized version no-op. | No gap. |

No critical silent gap found.

## Diagrams To Keep

Add inline ASCII comments where useful:

- `src/cortex/normalization/service.py`: pointer load -> normalize -> durable
  write -> publish flow.
- `src/cortex/normalization/result.py`: `NormalizationResult` shape.
- repository module: source object lifecycle transitions.

## Parallelization Strategy

| Step | Modules touched | Depends on |
| --- | --- | --- |
| Source object/file persistence | `src/cortex/db`, `alembic`, `tests/normalization` | — |
| Normalization result/registry | `src/cortex/normalization`, `tests/normalization` | — |
| Fixture normalizers | `src/cortex/normalization`, `tests/normalization` | Result contract |
| Publishers | `src/cortex/normalization`, `src/cortex/events`, `tests/normalization` | Persistence DTO shape |
| Service/worker integration | `src/cortex/normalization`, `src/cortex/workers`, `tests/workers` | Persistence + normalizers + publishers |
| Dev fixture integration | `src/cortex/dev`, `tests/dev` | Service/worker integration |

Parallel lanes:

- Lane A: persistence.
- Lane B: result/registry.
- Lane C: fixture normalizers after Lane B.
- Lane D: publishers after Lane A.
- Lane E: service/worker after A + C + D.
- Lane F: dev integration last.

Conflict flags: B, C, D, and E all touch `src/cortex/normalization`; define
interfaces first if parallelizing across worktrees.

## Completion Summary

- Step 0: Scope Challenge — scope accepted as-is.
- Architecture Review: 4 issues reviewed, corrections folded in.
- Code Quality Review: 3 issues reviewed, 1 mapper-test reminder remains.
- Test Review: diagram produced, 1 gap identified.
- Performance Review: 2 issues found.
- NOT in scope: written.
- What already exists: written.
- TODOs: none added.
- Failure modes: 0 critical gaps.
- Outside voice: skipped.
- Parallelization: 6 lanes, 2 early parallel lanes, rest dependency-sequenced.
- Lake Score: 4/4 recommendations choose the complete option.
