# Phase 3 Test Plan

## Commands

```bash
ruff check .
ruff format --check .
mypy src
pytest
```

Focused local loop:

```bash
pytest tests/contracts tests/ingestion tests/normalization tests/workers tests/dev
```

Optional database smoke when local Postgres is available:

```bash
docker compose up -d postgres
alembic upgrade head
pytest tests/normalization/test_source_object_repository.py
pytest tests/normalization/test_source_file_repository.py
```

## Coverage Map

```txt
Source object repository
  -> schema fields and indexes match v1 contract
  -> stable external identity upsert works
  -> same content hash no-ops
  -> changed content hash updates
  -> invalid lifecycle transitions reject

Source file repository
  -> diagram fixture creates stable source file
  -> file metadata and storage refs persist
  -> OCR text and OCR hash persist for fixture diagrams
  -> same content hash no-ops
  -> changed content hash updates
  -> filenames/file content are not logged or enveloped

Fixture normalizers
  -> Slack thread/message normalizes
  -> Slack diagram file normalizes to source object plus source file
  -> Linear issue normalizes
  -> GitHub PR normalizes
  -> repo doc section normalizes
  -> invalid payload shape returns structured error

Normalization service
  -> loads raw event and payload by pointer
  -> resolves provider/event-type normalizer
  -> upserts source objects/files before publishing
  -> marks raw event processed on success
  -> retryable failures update raw event state
  -> deadletter terminal failures after max attempts
  -> replay same raw event is idempotent
  -> normalized version change reprocesses

Publishers
  -> source_object.upserted envelope shape is correct
  -> source_file.fetched envelope shape is correct
  -> forbidden payload content is rejected
  -> no-op normalization does not publish

Relationship seeds
  -> fixture IDs link deterministically
  -> Linear issue IDs link deterministically
  -> GitHub PR numbers link deterministically
  -> URLs/file paths link deterministically
  -> replay no-ops existing seeds

Fixture integration
  -> existing Phase 1 dev tests still pass
  -> Phase 3 normalized fixture records match old deterministic IDs
```

## Tests To Create

| Test file | Assertions |
| --- | --- |
| `tests/normalization/test_source_object_repository.py` | Create/update/no-op, unique identity, content hash changes, lifecycle transitions. |
| `tests/normalization/test_source_file_repository.py` | Diagram file upsert, metadata/storage refs, OCR text/hash, content hash changes, no filename/OCR/content leakage. |
| `tests/normalization/test_fixture_normalizers.py` | Slack, Linear, GitHub, repo docs, diagram fixtures normalize into expected DTOs. |
| `tests/normalization/test_normalization_service.py` | Load by raw event pointer, upsert-before-publish, success, retry, deadletter, idempotent replay. |
| `tests/normalization/test_normalization_publishers.py` | Exact `source_object.upserted` and `source_file.fetched` envelopes. |
| `tests/normalization/test_relationship_seed_repository.py` | Deterministic seed IDs, replay no-op, normalized-version update behavior. |
| `tests/dev/test_fixture_seed_reset.py` | Preserve existing fixture counts and IDs after durable normalization integration. |
| `tests/dev/test_pipeline_run.py` | Timeline still reports normalize outputs and source object/file event IDs. |

## Golden Fixture Assertions

Minimum expected source objects:

- `so-slack-thread-sessions-postgres`
- `so-slack-file-session-flow-diagram`
- `so-linear-issue-COR-123`
- `so-linear-issue-COR-119`
- `so-github-pr-184`
- `so-repo-doc-session-storage`

Minimum expected source files:

- `file-slack-file-session-flow-diagram`

The diagram source file should include deterministic OCR fields:

```json
{
  "ocr_text_hash": "sha256:<stable>",
  "content_type": "image/png"
}
```

Minimum expected events:

```json
{
  "event_type": "source_object.upserted",
  "subject": {
    "type": "source_object"
  },
  "versions": {
    "normalized_version": "<fixture-normalizer-version>"
  },
  "payload": {
    "object_type": "<provider-neutral-type>",
    "operation": "upsert"
  }
}
```

```json
{
  "event_type": "source_file.fetched",
  "subject": {
    "type": "source_file"
  },
  "payload": {
    "content_type": "image/png",
    "operation": "upsert"
  }
}
```

Envelope payloads must not contain source text, OCR text, filenames, raw
payloads, file bytes, tokens, or secrets.

## Not Required In Phase 3

- real provider API calls,
- production OAuth/webhook tests,
- chunking and OCR worker tests,
- embedding/index/retrieval tests,
- context gate tests,
- browser tests,
- full graph ranking tests.
