# Ephemeral Cache Contract

Cortex cache backends are optional platform accelerators. They are safe to lose
at any time and must never become an authority for source data, permissions,
audit records, pipeline state, connector cursors, or user content.

## Backends

- `CORTEX_CACHE_BACKEND=memory` uses a process-local cache for tests and local
  development.
- `CORTEX_CACHE_BACKEND=redis` enables a Redis-compatible cache when
  `REDIS_URL` is configured and the runtime injects a Redis client.

Redis is not required for local development. If Redis is configured but
unavailable, callers must treat the cache as unavailable and fail closed for
controls such as rate limits or fall back only for non-authoritative performance
caches.

## Allowed Uses

- API, workspace, provider, and model-call rate-limit counters.
- Short-lived coordination locks when Postgres leases are not the better fit.
- Hot health snapshots that can be recomputed.
- Temporary query or retrieval results that can be recomputed from authoritative
  stores.

## Prohibited Uses

- Raw events, normalized source objects, chunks, embeddings, or canonical memory.
- Connector cursors, install records, source selections, permissions, or audit
  logs.
- Any value required to recover, rebuild, or prove system history.

Postgres, Kafka, the raw object store, and durable source repositories remain
the authoritative systems. Qdrant and OpenSearch are derived indexes and must be
rebuildable from durable records.
