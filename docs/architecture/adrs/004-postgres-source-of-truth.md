# ADR-004: Postgres Source Of Truth

## Status

Accepted.

## Decision

Use Postgres as the canonical source of truth for Cortex application data.

## What It Is

Postgres stores structured records for tenants, OAuth installs, source
connections, raw event metadata, source objects, chunks, files, permissions,
retrieval requests, evidence packs, canonical decisions, approvals, cursors,
worker state, and audit logs.

## Why Cortex Uses It

- Strong relational consistency for tenant/workspace/source boundaries.
- Mature migrations with Alembic.
- Good JSONB support for provider metadata.
- Good enough full-text search for the cheapest v1 lexical path.
- Easy to query/debug during early product development.

## Alternatives Considered

- Document database.
- Event store only.
- Search/vector database as primary store.

## Why Alternatives Lost

- Document databases are weaker for relational permission and audit queries.
- Event-store-only systems make product reads harder.
- Search/vector databases are derived indexes, not canonical transactional
  stores.

## Tradeoffs

- Large raw payloads should not live directly in Postgres forever.
- High-volume event payload storage may require object storage offload.
- Full-text search may eventually need OpenSearch.

## Failure Modes

- Storing large Slack files/images in Postgres can inflate storage and backups.
- Missing uniqueness constraints can create duplicate source objects.
- Poor migration discipline can break replay/rebuild behavior.

## How We Test It

- Migration tests.
- Unique idempotency tests for raw events/source objects/chunks.
- Replay tests that rebuild derived rows.
- Query tests for source health and evidence pack audit.

## How This Maps From CortexG

`cortexg` already modeled these tables in Postgres migrations. Cortex should
preserve and refine that schema in Python/Alembic.

