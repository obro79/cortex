# Phase 2 Test Plan

## Commands

```bash
ruff check .
ruff format --check .
mypy src
pytest
```

Focused local loop:

```bash
pytest tests/contracts tests/ingestion tests/workers tests/dev
```

Optional database smoke when local Postgres is available:

```bash
docker compose up -d postgres
alembic upgrade head
pytest tests/ingestion/test_raw_event_repository.py
```

## Coverage Map

```txt
Raw event model and repository
  -> table fields match v1 schema
  -> idempotency uniqueness works
  -> duplicate idempotency hash conflicts are rejected
  -> provider external_event_id uniqueness works
  -> invalid lifecycle transitions are rejected
  -> retry/deadletter fields update correctly
  -> replay candidates are ordered and scoped
  -> concurrent duplicate insert resolves to one row

Payload store
  -> canonical JSON hashing is deterministic
  -> nested JSON/list canonicalization hashes exact stored bytes
  -> payload_ref points to retrievable bytes
  -> duplicate payloads do not require duplicate content
  -> storage failures stop ingestion before DB insert

Ingestion service
  -> valid fixture/provider-shaped event persists
  -> duplicate idempotency key checks happen before payload write
  -> duplicate idempotency key with same hash no-ops
  -> duplicate idempotency key with different hash conflicts
  -> successful publish marks raw event published
  -> publish failure marks failed_retryable
  -> forbidden content never enters envelope payload

Pipeline envelope
  -> raw_event.persisted subject and causation are correct
  -> partition key is workspace plus external object key
  -> payload hash matches raw event row
  -> trace ID flows from ingestion to event

Worker skeleton
  -> consumes raw_event.persisted envelope
  -> loads raw event by subject pointer
  -> loads payload by payload_ref
  -> success path marks processed
  -> retryable load failure updates retry state
  -> max-attempt/terminal failure deadletters

Replay
  -> explicit raw event replay republishes pointer event
  -> replay creates a new envelope ID
  -> replay skips deleted raw events
  -> replay skips processing records unless explicitly requested by ID
  -> replay metadata is content-free
  -> replay order is deterministic

Fixture integration
  -> existing deterministic fixture tests still pass
  -> duplicate fixture seed still no-ops
  -> fixture raw events can be replayed
```

## Tests To Create

| Test file | Assertions |
| --- | --- |
| `tests/ingestion/test_payload_store.py` | Stable hashes, nested JSON/list canonicalization, payload refs, retrievable bytes, no content in logs/envelopes. |
| `tests/ingestion/test_raw_event_repository.py` | Create/get, unique constraints, idempotency hash conflicts, lifecycle transitions, replay candidate queries, concurrent duplicate insert. |
| `tests/ingestion/test_raw_event_ingestion.py` | Persist, duplicate same-hash no-op before payload write, duplicate different-hash conflict, publish success, publish failure, storage failure. |
| `tests/ingestion/test_raw_event_publisher.py` | Exact `raw_event.persisted` envelope shape, replay metadata, and forbidden payload protection. |
| `tests/workers/test_normalization_worker.py` | Consume/load success, retryable missing row/payload, deadletter after max attempts. |
| `tests/ingestion/test_raw_event_replay.py` | Replay by ID, replay by candidate query, skip deleted and processing records, deterministic order, batch pagination. |
| `tests/dev/test_fixture_seed_reset.py` | Preserve deterministic fixture seed behavior after durable integration. |
| `tests/dev/test_pipeline_run.py` | Pipeline timeline still reports raw event envelope IDs and trace IDs. |

## Golden Assertions

For a deterministic fixture raw event:

```json
{
  "status": "published",
  "event_type": "raw_event.persisted",
  "subject": {
    "type": "raw_event"
  },
  "hashes": {
    "payload_hash": "sha256:<stable>"
  },
  "payload": {
    "provider_event_type": "<small metadata only>"
  }
}
```

For duplicate ingestion:

```txt
same workspace_id + idempotency_key
  + same payload_hash
  -> returns existing raw_event.id
  -> does not write a second raw_events row
  -> does not write a second payload
  -> does not publish a second raw_event.persisted envelope

same workspace_id + idempotency_key
  + different payload_hash
  -> raises idempotency conflict
  -> does not overwrite existing raw_event.payload_ref
  -> does not publish
```

For replay:

```txt
existing raw_event.id
  -> new PipelineEventEnvelope.event_id
  -> same subject.id
  -> same payload_hash
  -> same payload_ref in loaded raw event
```

## Not Required In Phase 2

- real provider OAuth tests,
- webhook signature verification tests,
- Phase 3 source object creation tests,
- chunking/indexing/retrieval tests,
- browser tests,
- production Kafka cluster integration beyond the event bus boundary.
