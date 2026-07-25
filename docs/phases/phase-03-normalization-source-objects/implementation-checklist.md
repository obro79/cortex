# Phase 3 Implementation Checklist

## 1. Source Object Persistence

- Add `SourceObjectRecord` SQLAlchemy model and migration.
- Add indexes from `v1-entity-state-schema.md`.
- Keep `source_connection_id` indexed and required, without a foreign key unless
  the table already exists.
- Add repository methods:
  - `upsert_many`,
  - `get_by_id`,
  - `get_by_external_identity`,
  - `mark_stale`,
  - `mark_deleted`.
- Enforce `active`, `stale`, `superseded`, and `deleted` lifecycle rules.

Acceptance:

- stable external identity prevents duplicate source objects,
- same content hash no-ops,
- changed content hash updates the record,
- invalid lifecycle transitions are rejected.

## 2. Source File Persistence

- Add `SourceFileRecord` SQLAlchemy model and migration.
- Store metadata, storage refs, content hashes, content type, status, and trace
  ID.
- Add `ocr_text` and `ocr_text_hash` fields to the `SourceFile` contract/model
  if they are still missing.
- Do not store raw filenames in indexed/logged fields; use `file_name_hash`.
- Add repository methods for upsert, lookup by external file ID, stale, and
  deleted states.

Acceptance:

- Slack diagram fixture creates a stable source file,
- Slack diagram fixture persists OCR text and OCR hash for Phase 4,
- unchanged file content no-ops,
- changed file content updates hashes and metadata,
- source file content, OCR text, and filename are not logged or placed in
  envelopes.

## 3. Normalization Result Contract

- Add `NormalizationResult` and normalized record DTOs.
- Include raw event ID, normalized version, source objects, source files,
  relationship seeds, and optional skipped reason.
- Keep provider-specific details out of Phase 4-facing fields.

Acceptance:

- result objects serialize deterministically,
- invalid provider payload shapes produce structured errors,
- normalizer output does not include raw payload content in event payloads.

## 4. Fixture Normalizers

- Implement fixture normalizers for:
  - Slack thread/message,
  - Slack diagram file,
  - Linear issue,
  - GitHub PR,
  - repo doc section.
- Use Phase 2 raw payload bytes as source input.
- Generate stable IDs, external object keys, content hashes, canonical URLs, and
  normalized versions.

Acceptance:

- every Phase 1 fixture raw event normalizes,
- source object IDs are stable across replays,
- provider-neutral fields are populated consistently.

## 5. Normalization Service

- Add a service behind `handle_raw_event_persisted(envelope)`.
- Load raw event and payload by pointer.
- Resolve the normalizer from provider/event type.
- Upsert source objects/files and relationship seeds before publishing events.
- Mark raw event processed only after durable writes and successful required
  publications.
- Mark retryable/deadletter states using Phase 2 semantics for load, parse,
  upsert, or publish failures.

Acceptance:

- same raw event replay is idempotent,
- content hash changes update records and publish upsert events,
- publish failure leaves retryable state without losing durable objects.

## 6. Event Publishers

- Publish `source_object.upserted` after source object writes.
- Publish `source_file.fetched` after source file writes.
- Include subject, causation, normalized version, payload/content hashes, trace
  metadata, and small operation metadata.
- Reject source text, OCR text, filenames, file bytes, raw payloads, and secrets
  in envelope payloads.

Acceptance:

- exact envelope tests cover subject, causation, versions, hashes, trace, and
  payload keys,
- source object/file events are not published before durable writes,
- no-op normalization does not republish.

## 7. Relationship Seeds

- Add a narrow relationship seed repository or in-phase table if needed.
- Create deterministic seeds from fixture IDs, URLs, issue IDs, PR numbers, file
  paths, and parent references.
- Keep full graph expansion out of Phase 3.

Acceptance:

- COR-123 fixture produces expected deterministic relationship seeds,
- replay no-ops existing seeds,
- changed normalized version can recreate/update seeds deterministically.

## 8. Tests And Docs

- Add focused tests listed in [`test-plan.md`](test-plan.md).
- Update docs if implementation choices diverge.
- Keep Phase 2 raw-event tests in the focused loop.

Acceptance:

- `ruff check .` passes.
- `ruff format --check .` passes.
- `mypy src` passes.
- `pytest` passes.
- DB migration smoke passes against local Postgres when available.

## Completion Criteria

Phase 3 is complete when:

- durable source object/file persistence exists,
- fixture normalizers are deterministic and provider-neutral,
- idempotent replay/update behavior is tested,
- downstream source object/file events are pointer-only,
- relationship seeds are deterministic,
- Phase 4 can build chunking without reading raw provider payload shape.
