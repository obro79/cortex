# Phase 2 Plan: Raw Event Pipeline

## Goal

Persist provider-shaped input as durable raw events and publish lightweight
Kafka-style pointers that downstream workers can consume, retry, deadletter, and
replay.

This phase turns the Phase 1 fixture ingest boundary into the first production
pipeline stage:

```txt
fixture/provider-shaped input
  -> payload hash and optional object-storage write
  -> raw_events row
  -> raw_event.persisted PipelineEventEnvelope
  -> event bus publish
  -> normalization worker consumer skeleton
      -> load raw event by pointer
      -> mark processing outcome
```

Postgres and object storage are authoritative. Kafka carries only IDs, hashes,
routing keys, trace metadata, and small non-content metadata.

## Inputs

- [`../implementation-roadmap.md`](../implementation-roadmap.md#phase-2-raw-event-pipeline)
- [`../../architecture/v1-entity-state-schema.md`](../../architecture/v1-entity-state-schema.md#raw_events)
- [`../../architecture/pipeline-event-envelope.md`](../../architecture/pipeline-event-envelope.md)
- [`../../architecture/adrs/002-kafka-event-backbone/README.md`](../../architecture/adrs/002-kafka-event-backbone/README.md)
- [`../../architecture/adrs/004-postgres-source-of-truth/README.md`](../../architecture/adrs/004-postgres-source-of-truth/README.md)
- [`../phase-01-dev-workbench-fixtures/plan.md`](../phase-01-dev-workbench-fixtures/plan.md)

## Existing Foundation

Phase 0 and Phase 1 already provide:

- `src/cortex/contracts/entities.py`: `RawEvent` Pydantic contract with retry
  fields, payload refs, hashes, timestamps, status, and trace ID.
- `src/cortex/contracts/pipeline_events.py`: `PipelineEventEnvelope` with
  forbidden content-bearing payload key validation.
- `src/cortex/events/bus.py`: `EventBus` protocol and `KafkaEventBus`
  placeholder.
- `src/cortex/events/in_memory.py`: local event bus for unit tests.
- `src/cortex/interfaces/storage.py`: `ObjectStorage` protocol.
- `src/cortex/db/models.py`: SQLAlchemy model shell.
- `src/cortex/dev/fixtures.py`: deterministic fixture raw event creation that
  can be adapted to the durable ingestion path.
- `src/cortex/workers/main.py`: worker entrypoint shell.

## Non-Goals

- No real Slack, Linear, GitHub, or repo-doc OAuth.
- No webhook signature verification beyond fields needed by fixture ingest.
- No production provider backfill scheduler.
- No normalization into `source_objects`; Phase 3 owns that.
- No chunking, embeddings, indexing, retrieval, or context gate work.
- No custom distributed coordinator or custom Kafka replacement.
- No customer-facing admin UI.

## Architecture

```txt
Fixture/provider-shaped input
  -> RawEventIngestionService
      -> PayloadStore
          -> ObjectStorage for large payload bytes
          -> inline/local test storage for small deterministic tests
      -> RawEventRepository
          -> SQLAlchemy raw_events table
          -> idempotency constraints
      -> RawEventPublisher
          -> PipelineEventEnvelope(event_type="raw_event.persisted")
          -> EventBus publish
      -> status transition: received -> persisted -> published

NormalizationWorkerSkeleton
  -> consume raw_event.persisted envelope
  -> load raw_events row by subject.id
  -> load payload by payload_ref when needed
  -> mark processing / processed / failed_retryable / deadlettered
```

The implementation should keep storage, repository, publication, and worker
logic separate so Phase 3 can replace the consumer skeleton with real
normalizers without rewriting raw event persistence.

## Proposed Module Layout

```txt
src/cortex/ingestion/
  __init__.py
  raw_events.py
  payloads.py
  publisher.py

src/cortex/workers/
  normalization.py

tests/ingestion/
  test_raw_event_ingestion.py
  test_payload_store.py
  test_raw_event_repository.py
  test_raw_event_publisher.py

tests/workers/
  test_normalization_worker.py
```

If the current migration shell is incomplete, add the narrow Alembic pieces
needed for `raw_events` only.

## Data Model

Create the `raw_events` SQLAlchemy model and migration aligned with
`v1-entity-state-schema.md`.

Required fields:

| Field | Notes |
| --- | --- |
| `id` | Cortex raw event ID. |
| `workspace_id` | Tenant scope, required. |
| `source_connection_id` | Fixture or connector source, required for source-derived events. |
| `provider` | `slack`, `linear`, `github`, `repo_docs`, or `fixture`. |
| `external_event_id` | Provider event or deterministic fixture event ID. |
| `event_type` | Provider event type, not pipeline envelope type. |
| `external_object_key` | Stable provider-neutral routing key. |
| `idempotency_key` | Unique within workspace. |
| `payload_ref` | Object storage/local payload pointer. |
| `payload_hash` | `sha256:` hash of canonical payload bytes. |
| `payload_size_bytes` | Size of canonical payload bytes. |
| `occurred_at` | Provider occurrence time if known. |
| `received_at` | Ingestion time. |
| `published_at` | Set after successful event publication. |
| `processed_at` | Set by worker skeleton once consumed. |
| `status` | `RawEventStatus`. |
| retry fields | `attempt_count`, `last_error_code`, `last_error_message`, `next_retry_at`, `last_attempt_at`. |
| `trace_id` | Trace correlation across ingest and worker. |
| timestamps | `created_at`, `updated_at`. |

Phase 2 should store `source_connection_id` as a required indexed string, not a
foreign key. The connector/source connection table does not exist yet, and
adding it here would pull connector installation scope into the raw-event phase.
Add the foreign key when the connector model exists.

Required indexes:

- unique `(workspace_id, provider, external_event_id)`,
- unique `(workspace_id, idempotency_key)`,
- `(workspace_id, source_connection_id, received_at)`,
- `(workspace_id, status, next_retry_at)`,
- `(workspace_id, external_object_key)`.

## Payload Storage

Add a payload storage adapter that accepts canonical JSON bytes or raw bytes,
returns `payload_ref`, `payload_hash`, and size, and never logs content.

Phase 2 can use local/in-memory storage for tests and object-storage-compatible
interfaces for production shape. The important contract is that raw event rows
store pointers and hashes, not large provider payloads inline.

Canonical hashing rules:

- serialize fixture JSON with stable key ordering before hashing,
- prefix hashes with `sha256:`,
- hash the exact bytes referenced by `payload_ref`,
- make duplicate payload writes idempotent by hash-derived storage keys where
  practical.

## Ingestion Behavior

`RawEventIngestionService.ingest(...)` should:

1. Validate the provider, workspace, source connection, external event ID,
   idempotency key, and event type.
2. Canonicalize the payload bytes and compute the payload hash without writing
   the payload yet.
3. Check for an existing `(workspace_id, idempotency_key)`.
   - If the existing payload hash matches, return the existing raw event and do
     not write payload or publish again.
   - If the existing payload hash differs, raise a conflict and do not overwrite
     the row or payload ref.
4. Store the payload for new events only.
5. Insert the `raw_events` row with `persisted` status.
6. Publish a `raw_event.persisted` envelope after durable persistence.
7. Mark `published_at` and `status=published` after successful publication.
8. On publish failure, preserve the row and set retryable state.

Envelope rules:

- `subject.type` is `raw_event`.
- `subject.id` is the raw event ID.
- `partition_key` uses `{workspace_id}:{external_object_key}`.
- `causation.raw_event_id` is the raw event ID.
- `hashes.payload_hash` matches the raw event row.
- `payload` contains only small metadata such as provider event type.
- `payload` never contains raw provider content, source text, files, tokens, or
  secrets.

## Fixture Integration

Replace or wrap Phase 1 fixture raw event creation so fixture ingestion can use
the same raw-event service without requiring real OAuth. The workbench can still
remain deterministic and in-process, but Phase 2 should prove that fixture
events can be persisted, published, and replayed through the durable boundary.

Acceptance:

- existing Phase 1 fixture tests continue to pass,
- duplicate fixture events no-op by idempotency key,
- fixture raw event IDs and payload hashes remain deterministic.

## Worker Skeleton

Add a normalization worker skeleton as a direct handler:

```python
handle_raw_event_persisted(envelope: PipelineEventEnvelope) -> None
```

Do not add a full consumer abstraction in Phase 2. `EventBus` only models
publication today; adding Kafka consume semantics now would spend scope before
the handler behavior is proven.

The skeleton should:

- validate envelope type and subject,
- load the raw event by `subject.id`,
- load payload bytes through `payload_ref`,
- mark `processing`,
- call a placeholder normalization hook,
- mark `processed` on success,
- mark `failed_retryable` with retry fields on retryable errors,
- mark `deadlettered` after max attempts or terminal errors.

The hook should not create `source_objects`; Phase 3 owns real normalization.

## Replay

Add a replay path that can republish existing raw events by workspace, source
connection, status, or explicit IDs.

Minimum Phase 2 behavior:

- replay a single raw event by ID,
- replay multiple eligible raw events deterministically in received order,
- do not republish deleted events,
- exclude `processing` records from candidate replay unless explicitly replayed
  by ID,
- preserve original payload refs and hashes,
- create new envelope IDs while keeping `causation.raw_event_id`,
- include content-free replay metadata such as `replay_run_id`,
  `replay_reason`, or `requested_by` in the envelope payload.

Candidate replay queries must use a batch size and deterministic pagination by
`(received_at, id)` so workspace/source replays cannot become unbounded table
scans.

## Error Handling

| Failure | Required behavior |
| --- | --- |
| Duplicate idempotency key | Return existing raw event, do not write payload or publish duplicate event. |
| Duplicate idempotency key with different payload hash | Raise conflict, do not overwrite the existing row or payload ref. |
| Payload storage failure | Do not insert raw event row unless payload ref is durable. |
| DB insert failure after payload write | Leave payload addressable by hash; surface retryable ingest error. |
| Publish failure | Keep raw event row, set `failed_retryable`, record error, schedule retry. |
| Consumer cannot load raw event | Retry, then deadletter with envelope details and trace ID. |
| Consumer cannot load payload | Mark raw event retryable; deadletter after max attempts. |
| Forbidden envelope payload content | Contract validation fails before publication. |

## Observability

Log only IDs, hashes, counts, statuses, provider names, and trace IDs. Do not
log raw payload content.

Expose enough structured fields for later metrics:

- raw events received, persisted, published, failed, deadlettered,
- publish latency,
- consumer processing latency,
- retry count,
- deadletter reason code,
- replay count.

## Lifecycle Enforcement

Repository methods should enforce the raw event lifecycle from
`v1-entity-state-schema.md`:

```txt
received -> persisted -> published -> processing -> processed
                         -> failed_retryable -> published
                         -> deadlettered
processed -> deleted
```

Invalid status transitions should raise explicit errors in service code rather
than silently mutating rows. This keeps retry, replay, and deadletter behavior
auditable.

## Acceptance Criteria

Phase 2 is complete when:

- `raw_events` has a real SQLAlchemy model and migration.
- Raw payload storage returns durable refs, hashes, and sizes.
- Fixture ingestion persists raw events through the durable service.
- `raw_event.persisted` envelopes are published with pointer-only payloads.
- Duplicate fixture/provider events no-op by idempotency key.
- Publish and consume failures update retry/deadletter fields.
- The normalization worker skeleton loads raw events and payloads by pointer.
- Raw events can be replayed into the next stage.
- Focused tests and full repo validation pass.
