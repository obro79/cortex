# Phase 4 Plan: Chunking And Indexing Base

## Goal

Make normalized source objects and files searchable through source-aware chunks,
Postgres full-text search, deterministic local embeddings, and vector index
metadata.

Phase 4 starts where Phase 3 stops:

```txt
source_object.upserted / source_file.fetched
  -> source-aware chunker
  -> source_chunks
  -> source_chunk.upserted
  -> embedding_records
  -> embedding.requested / embedding.completed
  -> index_jobs
  -> Postgres FTS write
  -> VectorIndex adapter write
  -> index.requested / index.completed
```

Phase 4 builds searchable derived data. It does not implement the retrieval API,
ranking, evidence packs, or context gate.

## Inputs

- [`../implementation-roadmap.md`](../implementation-roadmap.md#phase-4-chunking-and-indexing-base)
- [`../../architecture/v1-entity-state-schema.md`](../../architecture/v1-entity-state-schema.md#source_chunks)
- [`../../architecture/pipeline-event-envelope.md`](../../architecture/pipeline-event-envelope.md)
- [`../../architecture/adrs/005-hybrid-retrieval-stack/README.md`](../../architecture/adrs/005-hybrid-retrieval-stack/README.md)
- [`../../architecture/adrs/005-hybrid-retrieval-stack/config-and-tuning.md`](../../architecture/adrs/005-hybrid-retrieval-stack/config-and-tuning.md)
- [`../../architecture/adrs/006-provider-neutral-embeddings/README.md`](../../architecture/adrs/006-provider-neutral-embeddings/README.md)
- [`../../architecture/adrs/007-source-aware-chunking/README.md`](../../architecture/adrs/007-source-aware-chunking/README.md)
- [`../phase-03-normalization-source-objects/plan.md`](../phase-03-normalization-source-objects/plan.md)

## Existing Foundation

Earlier phases provide:

- normalized `source_objects` and `source_files`,
- OCR text/hash on source files for fixture diagrams,
- source object/file pointer events,
- `SourceChunk`, `EmbeddingRecord`, and `IndexJob` Pydantic contracts,
- `PipelineEventEnvelope`,
- `VectorIndex` interface in `src/cortex/interfaces/vector_index.py`,
- Phase 1 fixture expectations for COR-123.

## Non-Goals

- No retrieval API or MCP retrieval tool.
- No ranking, evidence pack generation, or context gate.
- No production embedding provider calls. Dev/test uses deterministic
  embeddings only.
- No real Qdrant service requirement for unit tests.
- No OpenSearch adapter.
- No semantic extraction or relationship expansion.
- No permissions enforcement beyond storing workspace/source metadata needed for
  Phase 5 filters.

## Architecture

```txt
ChunkingService
  -> handle_source_object_upserted(envelope)
  -> handle_source_file_fetched(envelope)
      -> SourceObjectRepository / SourceFileRepository
      -> SourceAwareChunker
      -> SourceChunkRepository.upsert_many()
      -> SourceChunkPublisher.source_chunk.upserted
      -> EmbeddingJobService.enqueue_for_chunks()
      -> IndexJobService.enqueue_postgres_fts()

EmbeddingWorker
  -> handle_embedding_requested(envelope)
      -> SourceChunkRepository.get_by_id()
      -> DeterministicEmbeddingProvider.embed()
      -> EmbeddingRecordRepository.mark_completed()
      -> EmbeddingPublisher.embedding.completed
      -> IndexJobService.enqueue_qdrant()

IndexWorker
  -> handle_index_requested(envelope)
      -> PostgresFtsIndexer or VectorIndex adapter
      -> IndexJobRepository.mark_completed()
      -> IndexPublisher.index.completed
```

Postgres remains the source of truth for chunks, embedding metadata, and index
job state. FTS indexes and vector points are derived and rebuildable.

## Proposed Module Layout

```txt
src/cortex/chunking/
  __init__.py
  config.py
  result.py
  service.py
  source_aware.py
  publishers.py

src/cortex/embeddings/
  __init__.py
  deterministic.py
  service.py
  publishers.py

src/cortex/indexing/
  __init__.py
  postgres_fts.py
  service.py
  publishers.py

tests/chunking/
tests/embeddings/
tests/indexing/
```

Keep provider/source-specific chunking rules in `source_aware.py` until the file
becomes hard to scan.

## Data Model

Add SQLAlchemy records and migrations for:

- `source_chunks`,
- `embedding_records`,
- `index_jobs`.

Field sets, statuses, indexes, and lifecycle rules should match
`v1-entity-state-schema.md`.

`source_chunks.text` is customer content. It may be stored in Postgres for FTS
and later evidence citations, but it must never be logged, placed in pipeline
event payloads, or stored in vector index payload metadata.

Add Postgres full-text support for `source_chunks.text`. Prefer a generated
`tsvector` column or equivalent SQLAlchemy/Alembic migration that is explicit
and testable. Keep tenant/status/version filters index-backed.

## Chunking Config

Add a versioned YAML config file at
[`config/retrieval-v1.yaml`](../../../config/retrieval-v1.yaml), sourced from
`docs/architecture/adrs/005-hybrid-retrieval-stack/config-and-tuning.md`.

Load it through a typed config model instead of ad hoc dictionary access. The
typed loader should validate required sections, numeric bounds, source-specific
strategies, and version fields.

Initial chunking defaults:

```txt
global_min_chunk_tokens = 120
global_max_chunk_tokens = 1200
docs_target_tokens = 800
docs_overlap_tokens = 100
slack_thread_target_tokens = 600
slack_message_overlap_count = 1
linear_issue_target_tokens = 700
linear_comment_overlap_count = 1
github_pr_target_tokens = 900
ocr_target_tokens = 600
ocr_overlap_tokens = 100
```

The config also owns deterministic/prod embedding defaults, Phase 5 candidate
retrieval limits, and Phase 5 ranking weights. Phase 4 should use the chunking
and embedding sections; Phase 5 can extend usage to candidate retrieval and
ranking without moving the file.

Store the effective config/chunking version on every chunk. Changing the YAML
chunking section or `chunking.version` should mark affected chunks stale and
rebuild chunks, embeddings, and index jobs.

## Source-Aware Chunking

Implement deterministic fixture chunking for:

| Source | Chunks |
| --- | --- |
| Slack thread/message | overview chunk plus message/window chunks where fixture data supports it. |
| Linear issue | issue overview chunk and comment/blocker chunks where fixture data supports it. |
| GitHub PR | PR overview chunk and review/comment chunks where fixture data supports it. |
| Repo docs | markdown/doc section chunks. |
| Diagram/OCR | file metadata chunk plus OCR text chunk. |

Every chunk must include:

- stable chunk ID,
- source object/file refs,
- chunk type,
- chunk index,
- text,
- text hash,
- token count estimate,
- chunking version,
- citation label and URL,
- `created_from_hash`.

Chunk IDs should be deterministic by workspace, source object/file, chunk type,
chunk index, source content hash, and chunking version.

## Embeddings

Add a deterministic embedding provider for dev/test. It should:

- produce fixed-dimension vectors,
- be stable for the same input text hash and embedding version,
- produce different vectors for meaningfully different inputs,
- avoid external network calls.

Add embedding records for each active chunk:

- provider `deterministic` in dev/test,
- model name and dimensions,
- task type,
- embedding version,
- chunking version,
- input text hash,
- vector hash,
- Qdrant collection/point IDs after vector indexing,
- lifecycle status and retry fields.

Do not log embedding inputs or vectors. Vectors are derived and rebuildable.

## Indexing

Add index jobs for:

- Postgres FTS chunk upsert/delete/rebuild,
- Qdrant/vector upsert/delete/rebuild through the `VectorIndex` adapter.

The first implementation can use an in-memory `VectorIndex` test adapter and
keep a Qdrant adapter boundary for later. Application code should not call
Qdrant directly.

Vector payload metadata must include filterable fields only:

- workspace ID,
- source object ID,
- source chunk ID,
- provider,
- source type,
- chunk type,
- chunking version,
- embedding model/version,
- status.

Vector payloads must not include chunk text, source text, OCR text, filenames,
raw payloads, or secrets.

## Event Publication

Publish after durable state changes:

- `source_chunk.upserted` after chunk upserts,
- `embedding.requested` when an embedding record is queued,
- `embedding.completed` when deterministic embedding succeeds,
- `index.requested` when an index job is queued,
- `index.completed` after FTS/vector write succeeds.

Envelope payloads carry small metadata only: operation, chunk type, target store,
target type, model/dimensions, and versions. Never include chunk text, embedding
vectors, source text, OCR text, or secrets.

## Idempotency And Rebuilds

Rules:

- same source content hash plus same chunking version no-ops chunking,
- changed source content hash creates/updates chunks and marks old chunks stale,
- changed chunking version marks affected chunks stale and rebuilds,
- same chunk text hash plus same embedding version no-ops embedding,
- changed embedding version creates new embedding records,
- index jobs are idempotent by `(workspace_id, target_store, target_type,
  target_id, operation, index_version)`,
- stale/deleted chunks must enqueue FTS/vector cleanup jobs.

## Fixture Acceptance

For the COR-123 fixture bundle, Phase 4 should produce searchable chunks for:

- Slack Postgres-session decision,
- Slack diagram metadata and OCR text,
- Linear `COR-123`,
- Linear `COR-119`,
- GitHub PR `184`,
- stale repo session storage doc.

The fixture chunks should have stable citations and deterministic embeddings so
Phase 5 retrieval can evaluate exact candidates without network calls.

## Observability

Log only IDs, hashes, counts, statuses, versions, target stores, provider names,
and trace IDs.

Record:

- chunks created/updated/stale/deleted,
- embedding records queued/completed/failed,
- index jobs queued/completed/failed,
- FTS write latency,
- vector write latency,
- rebuild counts by version.

## Acceptance Criteria

Phase 4 is complete when:

- `source_chunks`, `embedding_records`, and `index_jobs` have SQLAlchemy records
  and migrations.
- Source-aware chunking covers fixture Slack, Linear, GitHub, repo docs, and OCR
  text.
- Chunk citations are stable and resolvable to source objects/files.
- Postgres full-text indexing has a smoke test.
- Deterministic embedding repeatability is tested.
- Vector indexing works through an adapter with a local/test implementation.
- Index jobs are idempotent by target, hash/version, operation, and index
  version.
- Pointer-only pipeline events are published for chunks, embeddings, and index
  jobs.
