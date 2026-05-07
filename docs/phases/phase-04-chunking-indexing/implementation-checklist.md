# Phase 4 Implementation Checklist

## 1. Persistence Models

- Add `SourceChunkRecord`, `EmbeddingRecord`, and `IndexJobRecord`.
- Add migrations, indexes, and lifecycle fields from
  `v1-entity-state-schema.md`.
- Add Postgres FTS support for `source_chunks.text`.
- Keep source chunk text out of logs and event payloads.

Acceptance:

- migrations create required tables and indexes,
- lifecycle status values match contract enums,
- FTS search can filter by workspace, status, and chunking version.

## 2. Chunking Config

- Add `config/retrieval-v1.yaml` with versioned chunking, embedding, candidate
  retrieval, and ranking defaults from `config-and-tuning.md`.
- Add a typed loader for the YAML file.
- Store `chunking_version` on every chunk.
- Make config available to chunking tests without environment-specific state.

Acceptance:

- config serializes deterministically,
- YAML defaults match ADR-005,
- typed loader rejects missing sections, invalid strategies, and invalid numeric
  bounds,
- changing chunking version can select stale/rebuild candidates,
- no magic chunk-size constants are hidden in chunker code.

## 3. Source-Aware Chunker

- Implement deterministic chunking for fixture:
  - Slack thread/message,
  - Linear issue,
  - GitHub PR,
  - repo doc section,
  - diagram metadata and OCR text.
- Generate stable chunk IDs, text hashes, citation labels/URLs, token counts,
  and `created_from_hash`.
- Mark unchanged chunks as no-op and old chunks stale when content/version
  changes.

Acceptance:

- every Phase 3 fixture source object/file creates expected chunks,
- chunk citation tests pass,
- chunk text is never logged or placed in event payloads.

## 4. Chunk Publisher

- Publish `source_chunk.upserted` after durable chunk writes.
- Include subject, causation, chunking version, content/text hashes, trace, and
  content-free operation metadata.
- Do not publish no-op chunks.

Acceptance:

- exact envelope tests cover subject, causation, hashes, versions, and payload,
- forbidden content-bearing payload keys are rejected.

## 5. Deterministic Embeddings

- Add deterministic embedding provider.
- Add embedding service to queue and complete embeddings for active chunks.
- Store provider, model, dimensions, task type, embedding version, chunking
  version, input text hash, vector hash, and status.
- Never log embedding input text or vectors.

Acceptance:

- same text hash/version produces the same vector hash,
- changed input or embedding version produces a different record/hash,
- embedding lifecycle and retry states are tested.

## 6. Vector Index Adapter

- Use `src/cortex/interfaces/vector_index.py`; do not call Qdrant directly.
- Add local/in-memory test adapter.
- Store filterable metadata only in vector payloads.
- Update embedding records with collection and point IDs after upsert.

Acceptance:

- adapter tests cover ensure collection, upsert, delete, search, and health,
- vector payloads exclude chunk text, source text, OCR text, filenames, and
  secrets.

## 7. Index Jobs

- Add index job service and repository.
- Queue Postgres FTS and vector index jobs.
- Enforce idempotency by workspace, target store/type/id, operation, and index
  version.
- Mark completed/failed/stale according to lifecycle rules.

Acceptance:

- duplicate index jobs no-op,
- failed jobs record retry fields,
- stale/deleted chunks enqueue cleanup jobs.

## 8. Index Publishers

- Publish `embedding.requested`, `embedding.completed`, `index.requested`, and
  `index.completed`.
- Keep envelopes pointer-only and content-free.

Acceptance:

- envelope tests cover exact event shapes,
- publish failures leave retryable job state,
- events are published only after durable state changes.

## 9. Tests And Docs

- Add focused tests listed in [`test-plan.md`](test-plan.md).
- Keep Phase 3 normalization tests in the focused loop.
- Update docs if implementation choices diverge.

Acceptance:

- `ruff check .` passes.
- `ruff format --check .` passes.
- `mypy src` passes.
- `pytest` passes.
- DB migration smoke passes against local Postgres when available.

## Completion Criteria

Phase 4 is complete when:

- normalized fixture records produce stable, cited chunks,
- chunks are searchable through Postgres FTS,
- deterministic embeddings and vector adapter writes work locally,
- index jobs are idempotent and retryable,
- all downstream events are pointer-only and content-free,
- Phase 5 can build retrieval over FTS/vector candidates.
