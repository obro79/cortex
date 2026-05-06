# ADR-021: Distributed Coordination Without Custom Leader

## Status

Accepted.

## Context

Cortex has multiple stores and workers: Postgres, Kafka, object storage, Qdrant,
future OpenSearch, API servers, connector workers, indexing workers, and
schedulers. It is tempting to add custom distributed storage or a single leader
service early, but that would increase operational complexity before the core
product loop is proven.

## Decision

Do not build custom distributed storage or a custom single-leader control plane
in v1.

Authority model:

- Postgres is the transactional source of truth.
- Kafka is the ordered event backbone for replayable pipeline work.
- Object storage stores large raw payloads, files, and OCR inputs.
- Qdrant and OpenSearch are derived indexes and can be rebuilt.
- Redis, if used, is ephemeral cache/coordination only.

Coordination model:

- Kafka consumer groups own stream-processing parallelism.
- Idempotency keys, content hashes, versioned jobs, and retries protect
  correctness.
- Singleton jobs use Postgres advisory locks or lease rows first.
- Redis locks are acceptable later only for short-lived coordination when Redis
  already exists.
- Kubernetes CronJobs or Temporal can replace simple scheduler leases when
  workflow complexity warrants it.

## Consequences

This keeps v1 understandable and recoverable. Derived indexes can be dropped and
rebuilt from source truth. Workers can scale horizontally without a bespoke
leader.

The tradeoff is that some scheduled jobs need careful lease expiry, retries, and
idempotency tests. That is still cheaper and safer than introducing a custom
coordination layer before scale requires it.

