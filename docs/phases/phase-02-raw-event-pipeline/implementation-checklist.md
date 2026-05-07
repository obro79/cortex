# Phase 2 Implementation Checklist

## 1. Raw Event Persistence

- Add `RawEventRecord` SQLAlchemy model for `raw_events`.
- Add a narrow Alembic migration for the table and indexes.
- Store `source_connection_id` as a required indexed string for Phase 2, not a
  foreign key.
- Add repository methods:
  - `create_or_get_by_idempotency_key`,
  - `get_by_id`,
  - `mark_published`,
  - `mark_processing`,
  - `mark_processed`,
  - `mark_failed_retryable`,
  - `mark_deadlettered`,
  - `mark_deleted`,
  - `list_replay_candidates`.
- Enforce allowed raw event lifecycle transitions.

Acceptance:

- unique constraints enforce provider event and idempotency duplicates,
- repository returns existing records for duplicate idempotency keys,
- repository rejects duplicate idempotency keys with a different payload hash,
- invalid status transitions are rejected,
- retry fields can be updated without mutating payload refs or hashes.

## 2. Payload Store

- Add a payload storage helper around `ObjectStorage`.
- Canonicalize JSON payloads with stable key ordering.
- Compute `sha256:` payload hashes.
- Return `payload_ref`, `payload_hash`, and `payload_size_bytes`.
- Add local/in-memory test implementation.

Acceptance:

- same payload produces same hash,
- stored bytes match hashed bytes,
- payload content is not logged or embedded in pipeline envelopes.

## 3. Ingestion Service

- Add `RawEventIngestionService`.
- Validate required provider/workspace/source/idempotency fields.
- Canonicalize and hash payload bytes before duplicate checks.
- Check idempotency before writing payload bytes.
- Store payload only for new events.
- Persist raw event with `persisted` status.
- Treat duplicate idempotency keys as no-op.
- Treat duplicate idempotency keys with different payload hashes as conflicts.
- Publish `raw_event.persisted`.
- Mark `published` and set `published_at` after successful publish.
- Mark retryable failure if publication fails.

Acceptance:

- fixture raw events persist through the service,
- duplicate fixture events do not republish,
- duplicate idempotency hash conflicts do not overwrite payload refs,
- publish failures leave replayable raw event rows.

## 4. Raw Event Publisher

- Add `RawEventPublisher` that builds `PipelineEventEnvelope`.
- Keep Kafka payload pointer-only and content-free.
- Use `workspace_id:external_object_key` partition keys.
- Include trace ID, payload hash, provider, source connection, and raw event
  causation.
- Keep `KafkaEventBus` as the production-shaped adapter boundary.

Acceptance:

- envelope validation rejects forbidden content keys,
- `raw_event.persisted` tests assert exact subject, causation, hashes, and
  partition key,
- event bus failures are surfaced to ingestion retry handling.

## 5. Fixture Path Integration

- Route Phase 1 fixture raw event creation through the raw event ingestion
  service where feasible.
- Preserve deterministic fixture IDs, timestamps, hashes, and counts.
- Keep `/dev/*` behavior guarded by `CORTEX_DEV_WORKBENCH_ENABLED`.

Acceptance:

- existing `tests/dev` and `tests/api/test_dev_endpoints.py` continue passing,
- duplicate fixture seed remains idempotent,
- fixture events can be replayed by raw event ID.

## 6. Normalization Worker Skeleton

- Add `src/cortex/workers/normalization.py`.
- Add `handle_raw_event_persisted(envelope)` as a direct handler.
- Validate envelope type and subject.
- Load raw event by pointer.
- Load payload bytes by `payload_ref`.
- Mark processing, then processed for the placeholder success path.
- Mark retryable/deadletter states for failures.

Acceptance:

- missing raw event retries then deadletters,
- missing payload retries then deadletters,
- success path does not create `source_objects`,
- worker emits structured status and trace metadata.

## 7. Replay

- Add replay service method for explicit raw event IDs.
- Add replay candidate listing by workspace/source/status.
- Republish new envelopes from existing raw event rows.
- Skip deleted events.
- Skip `processing` records in candidate replay unless explicitly replayed by ID.
- Add batch size and deterministic pagination by `(received_at, id)`.
- Add content-free replay metadata to republished envelopes.

Acceptance:

- replay creates new envelope IDs,
- replay preserves raw event ID, payload ref, payload hash, and causation,
- replay order is deterministic,
- replay metadata passes forbidden payload validation.

## 8. Tests And Docs

- Add focused tests listed in [`test-plan.md`](test-plan.md).
- Update docs if implementation diverges from this plan.
- Add run-log notes if any infra assumptions change.

Acceptance:

- `ruff check .` passes.
- `ruff format --check .` passes.
- `mypy src` passes.
- `pytest` passes.
- DB migration smoke passes against local Postgres when available.

## Completion Criteria

Phase 2 is complete when:

- raw events are durable,
- payloads are pointer-addressed and hashed,
- `raw_event.persisted` publication is pointer-only,
- retries/deadletters are recorded for publish and consume failures,
- fixture ingestion uses the same boundary as future connectors,
- replay into the worker skeleton works without creating Phase 3 objects.
