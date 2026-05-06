# ADR-014: Retention And Deletion

## Status

Accepted.

## Decision

Use configurable retention with a 90-day beta default for raw events/files, and
use hard delete plus minimal tombstones for deletion.

## What It Is

`RetentionPolicy` controls how long raw payloads, files, derived text, indexes,
canonical decisions, and audit metadata are kept. `DeletionRequest` coordinates
content removal across Postgres, object storage, Qdrant, and future OpenSearch.
`DeletionTombstone` preserves minimal non-content facts needed for audit,
idempotency, and replay safety.

## Why Cortex Uses It

- Hosted-first data requires a clear lifecycle.
- Replay/debug benefits from raw data, but indefinite retention increases
  privacy and storage risk.
- Deleted customer content must not remain retrievable.

## Alternatives Considered

- Keep raw data indefinitely.
- Derived-only storage after ingest.
- Soft delete only.
- Full purge with no tombstones.

## Why Alternatives Lost

- Indefinite raw retention raises trust and cost burden.
- Derived-only storage weakens replay and reindexing.
- Soft delete risks accidental retrieval.
- Full purge without tombstones makes idempotency/replay harder.

## Tradeoffs

- Deletion workflows must coordinate multiple stores.
- Tombstones need careful design to avoid retaining content.
- Short raw retention can reduce historical debugging fidelity.

## Failure Modes

- Deleted content remains in vector or lexical indexes.
- Tombstones accidentally include source titles, URLs, or excerpts.
- Retention jobs delete raw payloads before required reprocessing completes.

## How We Test It

- Deletion removes content from Postgres search, object storage, Qdrant, future
  OpenSearch, evidence output, and debug output.
- Tombstones contain no customer content.
- Retention jobs respect workspace/source overrides.
- Replay handles tombstoned events safely.

## How This Maps From CortexG

`cortexg` mentions deletion/retention in target docs but does not implement the
full lifecycle. Cortex designs it into v1.

