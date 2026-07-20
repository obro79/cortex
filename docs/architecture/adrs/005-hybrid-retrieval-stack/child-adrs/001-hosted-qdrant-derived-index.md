# ADR-005.1: Hosted Qdrant as a Derived Vector Index

## Status

Accepted — 2026-07-19.

## Context

ADR-005 selected Postgres FTS plus Qdrant for hybrid retrieval. Cortex has a Qdrant URL/API-key configuration seam and lifecycle deletion client, but no production upsert/search adapter or completed index pipeline. Postgres already stores canonical chunks, embedding provenance, and index-job metadata.

## Decision

Use **hosted Qdrant** for durable Cortex environments. Use persistent Docker Qdrant only for local development and Compose-backed integration testing.

Qdrant is a rebuildable, content-free derived index. Postgres remains the authority for chunks, permissions, citations, and deletions. Browser clients and MCP callers never receive Qdrant credentials or access Qdrant directly.

## Shape

- Collection identity: environment + embedding provider/model/version + dimensions.
- Point identity: deterministic embedding-record/chunk-version ID.
- Filterable payload: workspace ID, source chunk/object/file IDs, provider, active status, chunking/embedding/index version, and compact scope/ACL revision.
- Prohibited payload: source text, raw provider payloads, bytes, URLs, snippets, tokens, and secrets.
- Query policy: server-side workspace/status/version/provider/scope filter; then canonical Postgres hydration and a second permission check before any text is returned.
- Durability policy: an outbox/index job records intended delivery; worker delivery is idempotent; reconciliation and rebuild run from Postgres authority.

## Alternatives considered

1. Self-host Qdrant for the first durable environment.
2. Postgres/pgvector only.
3. Hosted Qdrant.

Self-hosting adds operational work without improving the product proof. pgvector-only reduces the number of services but conflicts with the accepted hybrid architecture and current vector-index abstraction. Hosted Qdrant is chosen because it gives the team a clean operational target while retaining a local deterministic test story.

## Consequences

- The production indexer, readiness projection, reconciliation, deletion, and observability work are mandatory before claiming durable hybrid retrieval.
- Hosted Qdrant availability must be separately reported; a lexical-only fallback is explicit partial retrieval, never silently `hybrid_ready`.
- Qdrant collections can be rebuilt and model versions can coexist during migration without altering canonical data.

## Required verification

- One canonical chunk produces one idempotent point; a restart preserves it.
- Workspace, status, version, provider, scope/ACL, deleted, and stale filters all behave correctly.
- Vector outage and Qdrant restart produce labeled partial/unavailable outcomes.
- A rebuild creates the expected point set from Postgres; deletion/revocation removes/tombstones it.
- No Qdrant payload or logs include protected source content or credentials.
