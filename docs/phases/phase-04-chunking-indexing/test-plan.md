# Phase 4 Test Plan

## Commands

```bash
ruff check .
ruff format --check .
mypy src
pytest
```

Focused local loop:

```bash
pytest tests/chunking tests/embeddings tests/indexing tests/normalization tests/dev
```

Optional database smoke when local Postgres is available:

```bash
docker compose up -d postgres
alembic upgrade head
pytest tests/indexing/test_postgres_fts.py
```

## Coverage Map

```txt
Persistence
  -> source_chunks schema/indexes/lifecycle
  -> embedding_records schema/indexes/lifecycle
  -> index_jobs schema/indexes/lifecycle
  -> Postgres FTS filters by workspace/status/version

Chunking config
  -> config/retrieval-v1.yaml defaults match config-and-tuning.md for chunking,
     embeddings, candidate retrieval, and ranking
  -> typed loader validates required sections
  -> typed loader rejects invalid strategies and numeric bounds
  -> chunking_version stored on chunks
  -> version change selects rebuild candidates

Source-aware chunking
  -> Slack decision chunks
  -> Linear issue chunks
  -> GitHub PR chunks
  -> repo doc section chunks
  -> diagram metadata and OCR chunks
  -> stable citations
  -> same content/version no-op
  -> changed content/version marks old chunks stale

Chunk events
  -> source_chunk.upserted exact envelope shape
  -> no chunk text in envelope payload
  -> no-op chunks do not publish

Embeddings
  -> deterministic repeatability
  -> changed input changes vector hash
  -> changed embedding version creates new record
  -> lifecycle retry/deadletter states
  -> no embedding inputs/vectors in logs

Vector index adapter
  -> ensure collection
  -> upsert points
  -> delete points
  -> search by workspace/status/version filters
  -> payload metadata excludes text/content/secrets

Index jobs
  -> FTS job idempotency
  -> vector job idempotency
  -> failed job retry fields
  -> deleted/stale chunks enqueue cleanup jobs
  -> index.requested/index.completed envelopes
```

## Tests To Create

| Test file | Assertions |
| --- | --- |
| `tests/chunking/test_chunking_config.py` | YAML defaults match ADR config; typed loader validates required sections, strategies, numeric bounds, and versions. |
| `tests/chunking/test_source_aware_chunker.py` | Slack, Linear, GitHub, repo docs, diagram metadata/OCR chunks and stable IDs. |
| `tests/chunking/test_source_chunk_repository.py` | Upsert/no-op/stale/delete lifecycle, citations, no content logs. |
| `tests/chunking/test_chunk_publishers.py` | Exact `source_chunk.upserted` envelope and forbidden payload protection. |
| `tests/embeddings/test_deterministic_provider.py` | Repeatable vectors/hashes, changed input/version behavior. |
| `tests/embeddings/test_embedding_service.py` | Queue/complete/retry/deadletter embedding records and events. |
| `tests/indexing/test_vector_index_adapter.py` | In-memory adapter collection/upsert/delete/search/health and metadata filters. |
| `tests/indexing/test_index_jobs.py` | Idempotent FTS/vector jobs, retry fields, stale/delete cleanup jobs. |
| `tests/indexing/test_postgres_fts.py` | FTS smoke search scoped by workspace, status, and chunking version. |
| `tests/indexing/test_index_publishers.py` | Exact `index.requested` and `index.completed` envelopes. |
| `tests/dev/test_pipeline_run.py` | Pipeline timeline reports chunk/embed/index outputs and event IDs. |

## Golden Fixture Assertions

Minimum fixture chunks:

- Slack Postgres-session decision chunk,
- Slack diagram metadata chunk,
- Slack diagram OCR text chunk,
- Linear `COR-123` issue chunk,
- Linear `COR-119` blocker chunk,
- GitHub PR `184` chunk,
- repo session storage doc chunk.

Minimum event assertions:

```json
{
  "event_type": "source_chunk.upserted",
  "subject": {
    "type": "source_chunk"
  },
  "versions": {
    "chunking_version": "<fixture-chunking-version>"
  },
  "payload": {
    "chunk_type": "<provider-neutral-type>",
    "operation": "upsert"
  }
}
```

```json
{
  "event_type": "embedding.completed",
  "subject": {
    "type": "embedding_record"
  },
  "payload": {
    "provider": "deterministic",
    "dimensions": "<dimension-count>"
  }
}
```

No envelope or vector payload may contain chunk text, source text, OCR text,
filenames, raw payloads, embeddings, vectors, tokens, or secrets.

## Not Required In Phase 4

- retrieval API tests,
- ranking/evidence-pack tests,
- context gate tests,
- real embedding provider tests,
- real Qdrant integration tests,
- OpenSearch tests,
- browser tests.
