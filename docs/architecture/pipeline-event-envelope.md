# Cortex Pipeline Event Envelope

## Purpose

Kafka carries lightweight pipeline events, not large provider payloads or full
normalized records. The event envelope tells workers what changed, where to load
the authoritative state from, and how to preserve ordering, idempotency, tracing,
and replay.

Authoritative state remains in Postgres and object storage:

- raw provider payloads live in `raw_events.payload_ref`,
- normalized objects live in `source_objects`,
- chunks live in `source_chunks`,
- vectors live in Qdrant with metadata in Postgres,
- evidence packs and gate results live in Postgres.

## Envelope Shape

Every Kafka message uses the same top-level envelope.

```json
{
  "event_id": "evt_01J...",
  "event_type": "raw_event.persisted",
  "schema_version": "pipeline-event-v1",
  "occurred_at": "2026-05-06T18:12:00Z",
  "published_at": "2026-05-06T18:12:03Z",
  "workspace_id": "ws_123",
  "source_connection_id": "src_456",
  "provider": "slack",
  "partition_key": "ws_123:slack:T123:C456:thread:1715000000.000100",
  "external_object_key": "slack:T123:C456:thread:1715000000.000100",
  "subject": {
    "type": "raw_event",
    "id": "raw_789"
  },
  "causation": {
    "raw_event_id": "raw_789",
    "source_object_id": null,
    "source_chunk_id": null,
    "retrieval_request_id": null
  },
  "versions": {
    "normalized_version": null,
    "chunking_version": null,
    "embedding_version": null,
    "index_version": null,
    "extractor_version": null,
    "gate_version": null
  },
  "hashes": {
    "payload_hash": "sha256:...",
    "content_hash": null,
    "text_hash": null,
    "vector_hash": null
  },
  "trace": {
    "trace_id": "trace_abc",
    "parent_event_id": null,
    "pipeline_run_id": "run_dev_123"
  },
  "producer": {
    "service": "ingestion-api",
    "instance_id": "api-1"
  },
  "retry": {
    "attempt": 0,
    "max_attempts": 5,
    "not_before": null
  },
  "payload": {}
}
```

## Field Rules

- `event_id`: unique event identifier. Use as Kafka message idempotency metadata.
- `event_type`: stable string that chooses the worker behavior.
- `schema_version`: starts at `pipeline-event-v1`; bump only on incompatible
  envelope changes.
- `workspace_id`: required for all events.
- `source_connection_id`: required for source-derived events; nullable for eval
  or admin events.
- `provider`: source provider when applicable.
- `partition_key`: Kafka key. Use `{workspace_id}:{external_object_key}` for
  source-derived events.
- `external_object_key`: stable provider-neutral routing key for the object.
- `subject`: the primary record the consumer should load from Postgres.
- `causation`: upstream record IDs for traceability and replay.
- `versions`: processing versions that determine whether downstream work is
  stale.
- `hashes`: content hashes used for idempotency and no-op detection.
- `trace`: distributed trace and dev workbench pipeline run linkage.
- `producer`: service identity for support and debugging.
- `retry`: retry metadata when republishing delayed work.
- `payload`: small event-specific metadata only. Do not put source content,
  provider payloads, chunks, embeddings, or secrets here.

## V1 Event Types

Use these event types for the first implementation.

| Event type | Topic | Subject | Produced by | Consumed by |
| --- | --- | --- | --- | --- |
| `raw_event.persisted` | `pipeline.raw-events` | `raw_event` | webhook/backfill ingestion | normalization workers |
| `source_object.upserted` | `pipeline.source-objects` | `source_object` | normalization workers | chunk/OCR, extraction, relationship workers |
| `source_object.deleted` | `pipeline.source-objects` | `source_object` | deletion/normalization workers | chunk/index cleanup workers |
| `source_file.fetched` | `pipeline.source-files` | `source_file` | file fetch workers | OCR/chunk workers |
| `source_chunk.upserted` | `pipeline.source-chunks` | `source_chunk` | chunk workers | embedding/index/extraction workers |
| `source_chunk.deleted` | `pipeline.source-chunks` | `source_chunk` | deletion/chunk workers | vector/search cleanup workers |
| `embedding.requested` | `pipeline.embeddings` | `embedding_record` | chunk workers | embedding workers |
| `embedding.completed` | `pipeline.embeddings` | `embedding_record` | embedding workers | vector index workers |
| `index.requested` | `pipeline.indexes` | `index_job` | chunk/embedding/deletion workers | index workers |
| `index.completed` | `pipeline.indexes` | `index_job` | index workers | freshness/eval workers |
| `semantic_artifact.upserted` | `pipeline.artifacts` | `semantic_artifact` | extraction workers | relationship/index workers |
| `relationship.upserted` | `pipeline.relationships` | `relationship` | relationship workers | retrieval freshness/eval workers |
| `evidence_pack.created` | `pipeline.retrieval` | `evidence_pack` | retrieval service | context gate workers/service |
| `context_gate.completed` | `pipeline.context-gate` | `context_gate_result` | context gate service | approval/audit workers |
| `canonical_decision.approved` | `pipeline.canonical-memory` | `canonical_decision` | approval service | chunk/index workers |
| `deletion.requested` | `pipeline.deletions` | `deletion_request` | API/admin service | deletion workers |
| `deletion.completed` | `pipeline.deletions` | `deletion_request` | deletion workers | audit/freshness workers |

## Examples

### Raw Event Persisted

```json
{
  "event_id": "evt_raw_123",
  "event_type": "raw_event.persisted",
  "schema_version": "pipeline-event-v1",
  "occurred_at": "2026-05-06T18:12:00Z",
  "published_at": "2026-05-06T18:12:03Z",
  "workspace_id": "ws_1",
  "source_connection_id": "src_slack_arch",
  "provider": "slack",
  "partition_key": "ws_1:slack:T123:C456:thread:1715000000.000100",
  "external_object_key": "slack:T123:C456:thread:1715000000.000100",
  "subject": {
    "type": "raw_event",
    "id": "raw_123"
  },
  "causation": {
    "raw_event_id": "raw_123",
    "source_object_id": null,
    "source_chunk_id": null,
    "retrieval_request_id": null
  },
  "versions": {
    "normalized_version": null,
    "chunking_version": null,
    "embedding_version": null,
    "index_version": null,
    "extractor_version": null,
    "gate_version": null
  },
  "hashes": {
    "payload_hash": "sha256:rawpayload",
    "content_hash": null,
    "text_hash": null,
    "vector_hash": null
  },
  "trace": {
    "trace_id": "trace_abc",
    "parent_event_id": null,
    "pipeline_run_id": "run_dev_1"
  },
  "producer": {
    "service": "ingestion-api",
    "instance_id": "api-1"
  },
  "retry": {
    "attempt": 0,
    "max_attempts": 5,
    "not_before": null
  },
  "payload": {
    "provider_event_type": "message.channels"
  }
}
```

### Source Object Upserted

```json
{
  "event_id": "evt_so_456",
  "event_type": "source_object.upserted",
  "schema_version": "pipeline-event-v1",
  "occurred_at": "2026-05-06T18:12:00Z",
  "published_at": "2026-05-06T18:12:06Z",
  "workspace_id": "ws_1",
  "source_connection_id": "src_slack_arch",
  "provider": "slack",
  "partition_key": "ws_1:slack:T123:C456:thread:1715000000.000100",
  "external_object_key": "slack:T123:C456:thread:1715000000.000100",
  "subject": {
    "type": "source_object",
    "id": "so_456"
  },
  "causation": {
    "raw_event_id": "raw_123",
    "source_object_id": "so_456",
    "source_chunk_id": null,
    "retrieval_request_id": null
  },
  "versions": {
    "normalized_version": "slack-thread-v1",
    "chunking_version": null,
    "embedding_version": null,
    "index_version": null,
    "extractor_version": null,
    "gate_version": null
  },
  "hashes": {
    "payload_hash": "sha256:rawpayload",
    "content_hash": "sha256:normalizedcontent",
    "text_hash": null,
    "vector_hash": null
  },
  "trace": {
    "trace_id": "trace_abc",
    "parent_event_id": "evt_raw_123",
    "pipeline_run_id": "run_dev_1"
  },
  "producer": {
    "service": "normalization-worker",
    "instance_id": "worker-1"
  },
  "retry": {
    "attempt": 0,
    "max_attempts": 5,
    "not_before": null
  },
  "payload": {
    "object_type": "slack_thread",
    "operation": "upsert"
  }
}
```

### Source Chunk Upserted

```json
{
  "event_id": "evt_chunk_789",
  "event_type": "source_chunk.upserted",
  "schema_version": "pipeline-event-v1",
  "occurred_at": "2026-05-06T18:12:00Z",
  "published_at": "2026-05-06T18:12:08Z",
  "workspace_id": "ws_1",
  "source_connection_id": "src_slack_arch",
  "provider": "slack",
  "partition_key": "ws_1:slack:T123:C456:thread:1715000000.000100",
  "external_object_key": "slack:T123:C456:thread:1715000000.000100",
  "subject": {
    "type": "source_chunk",
    "id": "chunk_789"
  },
  "causation": {
    "raw_event_id": "raw_123",
    "source_object_id": "so_456",
    "source_chunk_id": "chunk_789",
    "retrieval_request_id": null
  },
  "versions": {
    "normalized_version": "slack-thread-v1",
    "chunking_version": "slack-thread-chunker-v1",
    "embedding_version": null,
    "index_version": null,
    "extractor_version": null,
    "gate_version": null
  },
  "hashes": {
    "payload_hash": "sha256:rawpayload",
    "content_hash": "sha256:normalizedcontent",
    "text_hash": "sha256:chunktext",
    "vector_hash": null
  },
  "trace": {
    "trace_id": "trace_abc",
    "parent_event_id": "evt_so_456",
    "pipeline_run_id": "run_dev_1"
  },
  "producer": {
    "service": "chunk-worker",
    "instance_id": "worker-2"
  },
  "retry": {
    "attempt": 0,
    "max_attempts": 5,
    "not_before": null
  },
  "payload": {
    "chunk_type": "thread",
    "operation": "upsert"
  }
}
```

## Topic And Partition Rules

V1 topics are stage-oriented:

- `pipeline.raw-events`
- `pipeline.source-objects`
- `pipeline.source-files`
- `pipeline.source-chunks`
- `pipeline.embeddings`
- `pipeline.indexes`
- `pipeline.artifacts`
- `pipeline.relationships`
- `pipeline.retrieval`
- `pipeline.context-gate`
- `pipeline.canonical-memory`
- `pipeline.deletions`

Partition key:

```txt
{workspace_id}:{external_object_key}
```

For events that do not have a source object key, use:

```txt
{workspace_id}:{subject.type}:{subject.id}
```

## Consumer Rules

Workers must:

- validate `schema_version`,
- ignore event types they do not own,
- load authoritative state from Postgres/object storage by `subject`,
- use `event_id` and target record versions for idempotency,
- no-op when the referenced record is already processed at the same hash/version,
- preserve `trace_id` when publishing downstream events,
- publish downstream events only after durable state is committed,
- fail closed on permission ambiguity,
- never log `payload` if it may contain provider-specific identifiers.

## Retry And Deadletter Rules

Retryable failures:

- provider temporary errors,
- model provider rate limits,
- transient database/index writes,
- temporary object storage failures.

Terminal failures:

- invalid schema version,
- missing required subject record,
- invalid provider payload shape after retries,
- incompatible embedding dimensions,
- permission validation failure.

For retryable failures, update the owning Postgres job/entity state and
republish only when `next_retry_at` is due. Kafka is not the source of retry
truth; Postgres is.

Deadletter records must include:

- event ID,
- event type,
- subject,
- workspace ID,
- trace ID,
- error code,
- sanitized error message,
- attempt count.

## Do Not Put In Kafka

- raw Slack/Linear/GitHub payloads,
- source chunk text,
- OCR text,
- embeddings/vectors,
- OAuth tokens or secrets,
- private URLs in event payloads,
- full evidence pack contents,
- non-allowlisted source names, URLs, file names, snippets, or debug IDs.

