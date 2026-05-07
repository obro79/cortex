# Phase 2 Engineering Review

## Review Verdict

Status: approved with plan corrections recommended before implementation.

Scope challenge result: proceed as-is. Phase 2 intentionally touches several
module areas because the phase objective is the complete raw-event boundary:
persistence, payload refs, publication, retries/deadletters, worker pointer
loading, and replay.

## What Already Exists

| Sub-problem | Existing code | Reuse verdict |
| --- | --- | --- |
| Raw event API shape | `src/cortex/contracts/entities.py` | Reuse `RawEvent`; add DB record and mapping tests. |
| Pipeline envelope | `src/cortex/contracts/pipeline_events.py` | Reuse directly; keep payload pointer-only. |
| Local event publication | `src/cortex/events/in_memory.py` | Reuse for unit tests. |
| Kafka boundary | `src/cortex/events/bus.py` | Keep as adapter boundary; do not build full Kafka consumer in Phase 2. |
| Object storage boundary | `src/cortex/interfaces/storage.py` | Wrap with payload hashing/canonicalization helper. |
| DB base/migration shell | `src/cortex/db/*`, `alembic/` | Extend narrowly with `raw_events`. |
| Fixture raw event data | `src/cortex/dev/fixtures.py` | Adapt carefully; do not force all dev workbench tests to require Postgres. |
| Worker entrypoint | `src/cortex/workers/main.py` | Add normalization handler skeleton behind existing worker module. |

## NOT In Scope

- Real Slack, Linear, GitHub, or repo-doc OAuth: connector auth belongs to later
  connector phases.
- Production webhook signature verification: only fixture/provider-shaped ingest
  fields are needed now.
- Source object creation: Phase 3 owns normalization.
- Chunking, embeddings, indexing, retrieval, and context gate behavior: later
  phases own these derived layers.
- Full Kafka cluster integration tests: Phase 2 should keep unit tests on the
  event bus boundary and use Redpanda only for optional smoke work.
- Source connection table ownership: defer if absent; `raw_events` can keep
  `source_connection_id` as an indexed string until connector tables exist.

## Architecture Review

1. [P1] (confidence: 9/10) `plan.md:172-179`, `plan.md:238-246` — ingestion
   ordering conflicts with duplicate guarantees. The plan says to canonicalize
   and store the payload before handling duplicate idempotency, while the error
   table says duplicates must not write payload or publish duplicate events.

   Recommendation: hash/canonicalize first, check existing idempotency key and
   payload-hash conflict before storage, then store payload and insert/publish
   for new events only. This preserves explicitness and avoids duplicate object
   writes.

2. [P2] (confidence: 8/10) `plan.md:124-126` — `source_connection_id` is
   required, but the current repo has no `source_connections` table. Adding a
   foreign key now would drag connector scope into Phase 2.

   Recommendation: document that Phase 2 stores `source_connection_id` as a
   required indexed string without a foreign key until the connector/source
   connection table exists.

3. [P2] (confidence: 8/10) `plan.md:207-208` — the worker skeleton is described
   as consuming through `EventBus`, but `EventBus` only publishes. A consumer
   abstraction now risks overbuilding Kafka semantics.

   Recommendation: define Phase 2 worker scope as `handle_raw_event_persisted(
   envelope )`; test it directly with envelopes. Add a real consumer adapter
   only when Kafka consumption is implemented.

4. [P2] (confidence: 7/10) `plan.md:223-234` — replay can duplicate downstream
   work if the implementation has no replay reason/run ID and no protection
   against replaying already in-flight retry records.

   Recommendation: add `replay_reason`, `requested_by`, or `replay_run_id` to
   replay metadata in the envelope payload and restrict candidate replay to
   explicit statuses.

## Code Quality Review

1. [P2] (confidence: 8/10) `implementation-checklist.md:7-15` — repository
   methods are status-transition-heavy, but allowed transitions are not
   specified. This can lead to tests passing invalid state jumps.

   Recommendation: add a raw event lifecycle table to the plan and require
   repository methods to reject invalid transitions.

2. [P2] (confidence: 7/10) `plan.md:89-109` — module layout separates
   `raw_events.py`, `payloads.py`, and `publisher.py`, but fixture integration
   can still create a second raw-event path under `src/cortex/dev`.

   Recommendation: make `src/cortex/ingestion` the only place that creates
   production-shaped `RawEvent` objects; dev fixtures may call it through a
   test/local repository adapter.

3. [P3] (confidence: 7/10) `implementation-checklist.md:5` — the plan names
   `RawEventRecord`, while the Pydantic contract is `RawEvent`. Without mapping
   conventions, implementers may leak SQLAlchemy records into service outputs.

   Recommendation: require explicit mapper helpers or repository return DTOs
   and tests that `RawEvent` serialization remains stable.

## Test Review

Detected framework: Python, pytest, pytest-asyncio from `pyproject.toml`.

```txt
CODE PATHS                                            OPERATOR FLOWS
[+] RawEventIngestionService                          [+] Fixture/provider-shaped ingest
  ├── [★★  PLANNED] happy persist + publish              ├── [★★  PLANNED] seed fixtures
  ├── [GAP]        duplicate same hash before storage     ├── [GAP]        duplicate with different hash
  ├── [GAP]        duplicate different hash conflict      └── [★★  PLANNED] publish failure retry state
  ├── [★★  PLANNED] storage failure before DB insert
  └── [★★  PLANNED] publish failure after DB insert

[+] PayloadStore                                      [+] Replay
  ├── [★★  PLANNED] deterministic canonical hash         ├── [★★  PLANNED] replay by ID
  ├── [★★  PLANNED] retrievable payload_ref              ├── [★★  PLANNED] replay ordered candidates
  └── [GAP]        canonical bytes for nested JSON        └── [GAP]        replay in-flight failed_retryable

[+] RawEventRepository                                [+] Worker pointer load
  ├── [★★  PLANNED] unique constraints                    ├── [★★  PLANNED] raw event missing
  ├── [GAP]        invalid lifecycle transition            ├── [★★  PLANNED] payload missing
  └── [GAP]        concurrent duplicate insert race        └── [★★  PLANNED] success marks processed

[+] RawEventPublisher
  ├── [★★  PLANNED] envelope shape
  ├── [★★  PLANNED] forbidden payload protection
  └── [GAP]        replay metadata is content-free

COVERAGE: 18/25 paths planned (72%) | GAPS: 7
QUALITY: ★★★:0 ★★:18 ★:0
```

Missing test requirements to add:

- `tests/ingestion/test_raw_event_ingestion.py`: duplicate idempotency key with
  same hash returns existing record before payload write.
- `tests/ingestion/test_raw_event_ingestion.py`: duplicate idempotency key with
  different payload hash raises a conflict and does not overwrite payload refs.
- `tests/ingestion/test_payload_store.py`: nested JSON/list canonicalization
  hashes the exact stored bytes.
- `tests/ingestion/test_raw_event_repository.py`: invalid lifecycle transitions
  are rejected.
- `tests/ingestion/test_raw_event_repository.py`: concurrent duplicate insert
  resolves to one row.
- `tests/ingestion/test_raw_event_replay.py`: replay excludes in-flight
  `processing` records unless explicitly requested by ID.
- `tests/ingestion/test_raw_event_publisher.py`: replay metadata remains
  content-free and passes envelope validation.

## Performance Review

1. [P2] (confidence: 7/10) `plan.md:223-234` — replay by workspace/source/status
   can become an unbounded table scan if implemented without batch limits.

   Recommendation: require replay batch size, deterministic pagination by
   `(received_at, id)`, and an index-backed query.

2. [P3] (confidence: 7/10) `plan.md:153-166` — canonicalizing very large JSON
   payloads in memory is acceptable for Phase 2 tests, but real provider payloads
   and files can get large.

   Recommendation: explicitly limit Phase 2 JSON canonicalization to event
   metadata-sized payloads and store large file bytes through object storage
   without JSON reserialization.

## Failure Modes

| Codepath | Production failure | Planned handling | Gap |
| --- | --- | --- | --- |
| Ingest duplicate | Concurrent duplicate delivery races the unique constraint. | Unique indexes planned. | Add race test. |
| Payload store | Object storage write succeeds, DB insert fails. | Error table mentions retryable ingest error. | Add cleanup/idempotent rewrite note. |
| Publisher | Event bus publish times out after DB commit. | Mark retryable. | Good if transition is tested. |
| Worker load | Envelope references missing raw event. | Retry then deadletter. | Good. |
| Worker load payload | `payload_ref` object missing. | Retry then deadletter. | Good. |
| Replay | Operator replays too broad a status set. | Candidate filters planned. | Add batch/status guard. |
| Logging | Raw provider content reaches structured logs. | Observability section forbids content logs. | Add logging/redaction test. |

No silent critical gap found if the missing tests above are added.

## Diagrams To Keep

The plan already has useful data-flow diagrams. Add inline ASCII comments only
where they reduce ambiguity:

- `src/cortex/ingestion/raw_events.py`: raw event lifecycle state machine.
- `src/cortex/ingestion/publisher.py`: durable-write-before-publish sequence.
- `src/cortex/workers/normalization.py`: pointer-load and retry/deadletter flow.

## Parallelization Strategy

| Step | Modules touched | Depends on |
| --- | --- | --- |
| Persistence and migration | `src/cortex/db`, `alembic`, `tests/ingestion` | — |
| Payload store | `src/cortex/ingestion`, `src/cortex/interfaces`, `tests/ingestion` | — |
| Publisher/envelope | `src/cortex/ingestion`, `src/cortex/events`, `tests/ingestion` | Persistence contract |
| Worker skeleton | `src/cortex/workers`, `tests/workers` | Repository + payload store |
| Fixture integration | `src/cortex/dev`, `tests/dev`, `tests/api` | Ingestion service |
| Replay | `src/cortex/ingestion`, `tests/ingestion` | Repository + publisher |

Parallel lanes:

- Lane A: persistence and migration -> repository transitions.
- Lane B: payload store.
- Lane C: publisher after Lane A has record shape.
- Lane D: worker skeleton after Lanes A + B.
- Lane E: replay after Lanes A + C.
- Lane F: fixture integration last.

Conflict flags: Lane A, C, and E all touch `src/cortex/ingestion`; coordinate
interfaces first or keep these sequential in one worktree.

## TODOs Considered

No repo `TODOS.md` exists. Candidate TODOs, if you want one later:

- Add real Kafka/Redpanda consume integration after the handler skeleton is
  stable.
- Add `source_connections` table and foreign keys when connector installation
  work starts.
- Add operational replay CLI/admin endpoint after raw-event replay service
  proves out in tests.

## Completion Summary

- Step 0: Scope Challenge — scope accepted as-is.
- Architecture Review: 4 issues found.
- Code Quality Review: 3 issues found.
- Test Review: diagram produced, 7 gaps identified.
- Performance Review: 2 issues found.
- NOT in scope: written.
- What already exists: written.
- TODOs: 3 candidates identified, not added because no `TODOS.md` exists.
- Failure modes: 0 critical silent gaps if test gaps are added.
- Outside voice: skipped.
- Parallelization: 6 lanes, 2 early parallel lanes, rest dependency-sequenced.
- Lake Score: 4/4 recommendations choose the more complete option.
