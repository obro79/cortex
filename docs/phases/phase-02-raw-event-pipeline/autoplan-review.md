# Phase 2 Autoplan Review

## Review Scope

Plan reviewed:

- [`plan.md`](plan.md)
- [`implementation-checklist.md`](implementation-checklist.md)
- [`test-plan.md`](test-plan.md)
- [`../implementation-roadmap.md`](../implementation-roadmap.md#phase-2-raw-event-pipeline)
- [`../../architecture/v1-entity-state-schema.md`](../../architecture/v1-entity-state-schema.md#raw_events)
- [`../../architecture/pipeline-event-envelope.md`](../../architecture/pipeline-event-envelope.md)
- Existing Phase 0/1 code in `src/cortex/contracts`, `src/cortex/events`,
  `src/cortex/interfaces`, `src/cortex/dev`, `src/cortex/db`, and
  `src/cortex/workers`.

Autoplan mode:

- CEO review: wedge value, scope boundary, sequencing, and non-goals.
- Design review: skipped because Phase 2 has no user-facing UI changes.
- Engineering review: architecture, data flow, retries, replay, test coverage,
  and failure modes.
- DX review: focused on local fixture workflow, migration ergonomics, and worker
  smokeability.

Dual voice status:

- Codex CLI: unavailable as a separate reviewer in this session.
- Claude-style subagents: not invoked under this session policy.
- Degradation: single-reviewer mode using the local gstack autoplan methodology.

## Executive Verdict

Phase 2 is approved for implementation with one strict correction: this phase
must be the durable raw-event boundary, not the beginning of provider connector
or normalization scope.

The strongest plan is to make raw event persistence, pointer-only publication,
idempotency, retry/deadletter state, and replay boring and testable. Phase 3 can
then focus on actual normalization without also proving the ingestion substrate.

## CEO Review

Score: 8/10.

### Premise Challenge

| Premise | Verdict | Reasoning |
| --- | --- | --- |
| Raw provider input should be persisted before downstream work. | Accepted | Replay, audit, deletion, and debugging all depend on this durable boundary. |
| Kafka should carry pointers instead of payloads. | Accepted | This matches the architecture docs and keeps secrets/customer content out of the event stream. |
| Fixture ingestion can validate Phase 2 without OAuth. | Accepted | It proves the storage/publication contract while keeping connectors for later phases. |
| A worker skeleton is enough before normalization exists. | Accepted | The consumer must prove pointer loading and retry state; source object creation belongs to Phase 3. |

### Scope Decisions

| Decision | Classification | Result |
| --- | --- | --- |
| Add only the `raw_events` production table in this phase. | Scope discipline | Accepted |
| Route fixtures through the durable raw-event service. | Product leverage | Accepted |
| Keep real provider OAuth/webhooks out. | Scope control | Accepted |
| Implement pointer-only `raw_event.persisted` publication. | Architectural invariant | Accepted |
| Add replay now. | Completeness | Accepted |
| Defer source object writes. | Phase boundary | Accepted |

### Product Story

After Phase 2, a developer can point at a fixture/provider-shaped input and
answer:

```txt
Was the provider event received?
Where is the exact payload stored?
What hash identifies it?
Was a downstream pointer published?
Can the worker reload it by pointer?
Can we replay it without re-calling the provider?
```

That is the right product value for this phase. It is not yet about whether
Cortex understands the content.

## Engineering Review

Score: 8/10.

### Architecture Diagram

```txt
tests/ingestion
  -> RawEventIngestionService
      -> PayloadStore
      -> RawEventRepository
      -> RawEventPublisher
          -> PipelineEventEnvelope
          -> EventBus

tests/workers
  -> NormalizationWorkerSkeleton
      -> RawEventRepository.get_by_id(subject.id)
      -> PayloadStore.get(payload_ref)
      -> retry/deadletter transitions
```

### Findings

1. Duplicate handling must happen before publish.
   Decision: repository create should be idempotent by `(workspace_id,
   idempotency_key)`, and duplicate ingestion must return existing rows without
   emitting duplicate envelopes.

2. Publish failure must not lose persisted work.
   Decision: store raw event first, publish second, then mark `published`. If
   publish fails, mark `failed_retryable` and leave replay metadata intact.

3. Payload hashing can drift if JSON serialization is casual.
   Decision: canonical JSON serialization is part of the payload store contract
   and covered by tests.

4. Worker skeleton can accidentally become Phase 3.
   Decision: worker may load payload and call a placeholder hook, but it must
   not create `source_objects` in Phase 2.

5. Replay can duplicate downstream work if envelope IDs are reused.
   Decision: replay creates new envelope IDs but preserves raw event subject,
   causation, payload hash, and partition key.

### Data Flow

```txt
ingest request
  -> canonical payload bytes
  -> payload store put
  -> raw_events insert
  -> raw_event.persisted envelope
  -> event bus publish
  -> raw_events.published_at/status update

consumer
  -> envelope subject
  -> raw_events select
  -> payload store get
  -> processing status
  -> placeholder normalize
  -> processed or retry/deadletter status
```

### Edge Cases

| Edge case | Expected handling |
| --- | --- |
| Same provider event delivered twice | Existing raw event returned; no duplicate publish. |
| Same idempotency key with different payload hash | Treat as conflict or terminal validation error; do not overwrite payload ref. |
| Payload storage succeeds and DB insert fails | Report retryable ingest failure; content remains addressable by hash. |
| DB insert succeeds and publish fails | Mark retryable and allow replay/republish. |
| Consumer receives unsupported event type | Ignore or reject without mutating raw event state. |
| Raw event is deleted before replay | Skip replay. |

## DX Review

Score: 8/10.

The developer loop should stay narrow:

```txt
pytest tests/ingestion tests/workers
alembic upgrade head
pytest tests/dev
```

The plan should make failures obvious by including raw event IDs, idempotency
keys, payload hashes, trace IDs, and status transitions in assertion messages
and structured logs. It should not require real provider credentials, live
Kafka, or live object storage for the normal unit-test loop.

## Risks

| Risk | Mitigation |
| --- | --- |
| Overbuilding Kafka infrastructure | Keep `EventBus` protocol and test with in-memory bus first. |
| Leaking payload content into events/logs | Contract validation plus logging tests. |
| Migration churn | Add only `raw_events` now. |
| Fixture determinism regression | Keep Phase 1 tests in the focused loop. |
| Replay semantics unclear | Test new envelope ID plus preserved subject/hash/causation. |

## Final Approval Gate

Approved to implement if the team accepts these constraints:

- Phase 2 owns durable raw events and pointer publication only.
- Phase 3 owns normalized source objects.
- Phase 2 tests must prove idempotency, retry/deadletter state, and replay.
- No raw provider payload content may be carried in Kafka envelopes or logs.
