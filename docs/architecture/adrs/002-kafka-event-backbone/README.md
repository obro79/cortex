# ADR-002: Kafka Event Backbone

## Status

Accepted.

## Decision

Use Kafka infrastructure as the durable event backbone for ingestion,
normalization, chunking, embedding, indexing, extraction, and replay.

ADR-022 narrows the runtime implementation to Apache Kafka.

## What It Is

Kafka is an append-only distributed event log. Cortex workers consume events by
topic and partition, process them, and write derived state back to Postgres,
object storage, Qdrant, and future OpenSearch indexes.

## Why Cortex Uses It

- Connector ingestion needs backfill, webhook, retry, and replay semantics.
- Slack/GitHub/Linear events can arrive continuously and out of order.
- Kafka partitioning lets Cortex preserve per-source-object ordering while
  processing many objects in parallel.
- Replay is central to rebuilding derived objects and indexes from raw truth.

## Partition Key

Use:

```text
{workspace_id}:{source_object_key}
```

Examples:

- `workspace:slack:{team_id}:{channel_id}:{thread_ts}`
- `workspace:linear:{issue_id}`
- `workspace:github:{repo_id}:pr:{number}`
- `workspace:doc:{repo_id}:{path}`

## Alternatives Considered

- Postgres outbox/jobs.
- Celery.
- Temporal.

## Why Alternatives Lost

- Postgres jobs are cheaper early but become awkward for high-volume replay and
  partitioned connector ingestion.
- Celery is familiar for Python background jobs, but Kafka is cleaner as the
  canonical event log.
- Temporal is excellent for long-running workflows but is a larger platform
  commitment than v1 needs.

## Tradeoffs

- Kafka adds operational complexity.
- Workers need idempotency and offset/retry discipline.
- Local development needs a Kafka dependency.

## Failure Modes

- Bad partition keys can serialize too much work or break ordering.
- Poison events can cause repeated worker failures without deadletter handling.
- Consumer lag can make context stale.

## How We Test It

- Partition key stability tests.
- Idempotent replay tests.
- Deadletter tests for poison events.
- Consumer lag and retry behavior tests.

## How This Maps From CortexG

`cortexg` has an `event_queue` abstraction and event topics. Cortex keeps the
topic lifecycle but upgrades the queue into Kafka-compatible infrastructure.
