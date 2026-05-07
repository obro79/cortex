# Phase 3 Plan: Normalization And Source Objects

## Goal

Turn provider-shaped raw events into provider-neutral Cortex source objects,
source files, and deterministic relationship seeds.

Phase 3 starts where Phase 2 stops:

```txt
raw_event.persisted envelope
  -> load raw_events row and payload_ref
  -> provider fixture normalizer
  -> source_objects upsert
  -> source_files upsert for file/diagram records
  -> deterministic relationship seeds
  -> source_object.upserted / source_file.fetched events
```

The output must be neutral enough that Phase 4 chunking can ignore raw provider
payload shape.

## Inputs

- [`../implementation-roadmap.md`](../implementation-roadmap.md#phase-3-normalization-and-source-objects)
- [`../../architecture/v1-entity-state-schema.md`](../../architecture/v1-entity-state-schema.md#source_objects)
- [`../../architecture/pipeline-event-envelope.md`](../../architecture/pipeline-event-envelope.md)
- [`../../architecture/adrs/011-slack-files-diagrams-ocr/README.md`](../../architecture/adrs/011-slack-files-diagrams-ocr/README.md)
- [`../phase-01-dev-workbench-fixtures/plan.md`](../phase-01-dev-workbench-fixtures/plan.md)
- [`../phase-02-raw-event-pipeline/plan.md`](../phase-02-raw-event-pipeline/plan.md)

## Existing Foundation

Phase 0-2 provide or plan:

- `RawEvent`, `SourceObject`, and `SourceFile` Pydantic contracts.
- `PipelineEventEnvelope` with pointer-only payload validation.
- Durable `raw_events` table, payload refs, and replay path from Phase 2.
- Normalization worker handler shell from Phase 2.
- Phase 1 deterministic fixture data for Slack, Linear, GitHub, repo docs, and
  diagram/OCR sources.

## Non-Goals

- No real provider OAuth, webhooks, or backfill scheduling.
- No generic production Slack/Linear/GitHub connector coverage beyond fixture
  payload shapes.
- No chunking, embeddings, full-text indexing, Qdrant writes, retrieval, or
  context gate work.
- No model-backed OCR or vision reasoning. Fixture diagram OCR text can be
  carried as metadata/content for later chunking.
- No permissions enforcement beyond preserving workspace/source IDs and
  source-allowlist metadata placeholders.
- No new Kafka consumer framework beyond the handler boundary created in Phase 2.

## Architecture

```txt
NormalizationWorker
  -> handle_raw_event_persisted(envelope)
      -> RawEventRepository.get_by_id(envelope.subject.id)
      -> PayloadStore.get(raw_event.payload_ref)
      -> NormalizerRegistry.for_provider(raw_event.provider, raw_event.event_type)
      -> NormalizationResult
          -> source_objects[]
          -> source_files[]
          -> relationships[]
      -> SourceObjectRepository.upsert_many()
      -> SourceFileRepository.upsert_many()
      -> RelationshipSeedRepository.upsert_many()
      -> SourceObjectPublisher.publish_upserted()
      -> SourceFilePublisher.publish_fetched()
      -> mark raw_event processed
```

All persistence happens before downstream events are published. Downstream
events carry source object/file IDs, hashes, versions, and small operation
metadata only.

## Proposed Module Layout

```txt
src/cortex/normalization/
  __init__.py
  registry.py
  result.py
  service.py
  publishers.py
  normalizers/
    __init__.py
    fixtures.py

src/cortex/db/models.py
  SourceObjectRecord
  SourceFileRecord
  RelationshipSeedRecord

tests/normalization/
  test_fixture_normalizers.py
  test_normalization_service.py
  test_source_object_repository.py
  test_source_file_repository.py
  test_relationship_seed_repository.py
  test_normalization_publishers.py
```

The first implementation can keep fixture normalizers in one module. Split by
provider only when that file becomes hard to scan.

## Data Model

Add `source_objects` and `source_files` SQLAlchemy records plus migrations.

`source_objects` follows `v1-entity-state-schema.md`:

- unique `(workspace_id, provider, object_type, external_object_id)`,
- index `(workspace_id, external_object_key)`,
- index `(workspace_id, object_type, source_updated_at)`,
- index `(workspace_id, status)`,
- index `(workspace_id, content_hash)`.

`source_files` should align with the existing `SourceFile` contract and
ADR-011. Add OCR fields to the contract/model in this phase if they are still
missing:

- `id`,
- `workspace_id`,
- `source_object_id`,
- `source_connection_id`,
- `provider`,
- `external_file_id`,
- `external_object_key`,
- `file_name_hash`,
- `content_type`,
- `storage_ref`,
- `content_hash`,
- `ocr_text`,
- `ocr_text_hash`,
- `metadata_json`,
- `status`,
- `trace_id`,
- `created_at`,
- `updated_at`,
- `deleted_at`.

`ocr_text` is customer content. It may be persisted for fixture diagrams so
Phase 4 can chunk it, but it must never be logged or placed in pipeline envelope
payloads.

Do not add a `source_connections` foreign key in Phase 3 unless Phase 2 has
already introduced the table. Keep `source_connection_id` indexed and required
for source-derived records.

Add a narrow relationship seed table only if needed for deterministic Phase 3
links. It should store IDs, object refs, relationship type, confidence, trace ID,
and the raw event/normalization version that produced it. Do not build the full
relationship graph service in this phase.

## Normalization Contract

Normalizers should return a provider-neutral `NormalizationResult`:

```txt
NormalizationResult
  raw_event_id
  normalized_version
  source_objects[]
  source_files[]
  relationship_seeds[]
  skipped_reason?
```

Each normalized source object must include:

- stable ID derived from workspace/provider/object type/external object ID,
- provider-neutral `object_type`,
- `external_object_id`,
- `external_object_key`,
- title/canonical URL when available,
- source timestamps,
- `normalized_version`,
- `content_hash`,
- non-content `metadata_json`,
- trace ID.

Provider-specific raw payload shape must not leak into Phase 4-facing fields.
Provider-specific details may be kept in `metadata_json` only when useful for
debugging and not content-bearing or secret-bearing.

## Fixture Normalizers

Implement deterministic normalizers for the Phase 1 fixture bundle:

| Provider shape | Output |
| --- | --- |
| Slack decision thread/message | `source_object` with `object_type=slack_thread` or `slack_message`. |
| Slack diagram file | `source_object` for the parent file/thread plus `source_file` with OCR metadata. |
| Linear issue | `source_object` with `object_type=linear_issue`. |
| GitHub PR | `source_object` with `object_type=github_pull_request`. |
| Repo doc | `source_object` with `object_type=repo_doc_section`. |

The normalizers should use the durable Phase 2 payload bytes for source content,
not the Phase 1 in-memory `source_objects` as the source of truth. Phase 1
fixture data can still provide deterministic raw payload builders for tests.

## Idempotency And Updates

Upsert behavior:

- replaying the same raw event with the same `content_hash` is a no-op,
- changed `content_hash` updates the active record and republishes
  `source_object.upserted`,
- if the normalized version changes, reprocess even when raw payload hash is the
  same,
- deleted raw events are not normalized,
- invalid provider payload shape marks the owning raw event retryable or
  deadlettered according to Phase 2 retry rules.

Keep source object IDs stable across replays. Do not generate random IDs.

## Event Publication

Publish `source_object.upserted` after durable source object upserts.

Envelope rules:

- `subject.type=source_object`,
- `subject.id` is the source object ID,
- `causation.raw_event_id` and `causation.source_object_id` are set,
- `versions.normalized_version` is set,
- `hashes.payload_hash` and `hashes.content_hash` are set,
- `trace.parent_event_id` points to the raw event envelope when available,
- `payload` contains small metadata only: `object_type`, `operation`, and
  relationship/file counts.

Publish `source_file.fetched` after durable source file upserts.

Envelope rules:

- `subject.type=source_file`,
- `subject.id` is the source file ID,
- `causation.raw_event_id` and `causation.source_object_id` are set,
- `hashes.payload_hash` and `hashes.content_hash` are set,
- `payload` contains content-free metadata such as content type and operation.

Never put source text, OCR text, filenames, raw payloads, tokens, or file bytes
inside envelope payloads.

## Relationship Seeds

Create deterministic relationship seeds for the fixture set:

- Linear issue ID references like `COR-123`,
- GitHub PR numbers like `#184`,
- canonical URLs,
- fixture IDs,
- file/thread parent references,
- repo file paths when present.

Relationship seed IDs must be deterministic by workspace, relationship type,
source ref, target ref, and normalization version. Full graph expansion and
ranking belong to later relationship/retrieval phases.

## Observability

Log only IDs, provider names, object types, hashes, counts, statuses, and trace
IDs. Do not log source text, OCR text, filenames, raw payload content, or raw
provider JSON.

Record counters/timers for:

- raw events normalized,
- source objects inserted/updated/no-op,
- source files inserted/updated/no-op,
- relationship seeds created/no-op,
- normalization failures by provider and error code,
- publish failures by event type.

## Acceptance Criteria

Phase 3 is complete when:

- `source_objects` and `source_files` have SQLAlchemy records and migrations.
- Fixture raw events normalize into stable source object and file IDs.
- Replaying the same raw event is idempotent.
- Content hash changes produce updates; unchanged content no-ops.
- Normalized records are provider-neutral enough for Phase 4 chunking to ignore
  raw payload shape.
- `source_object.upserted` and `source_file.fetched` events are published after
  durable writes.
- Deterministic relationship seeds exist for fixture IDs, URLs, PR numbers, file
  paths, and issue IDs.
- Focused tests and full repo validation pass.
