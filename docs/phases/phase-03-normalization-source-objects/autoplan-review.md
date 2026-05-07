# Phase 3 Autoplan Review

## Review Scope

Plan reviewed:

- [`plan.md`](plan.md)
- [`implementation-checklist.md`](implementation-checklist.md)
- [`test-plan.md`](test-plan.md)
- [`../implementation-roadmap.md`](../implementation-roadmap.md#phase-3-normalization-and-source-objects)
- [`../../architecture/v1-entity-state-schema.md`](../../architecture/v1-entity-state-schema.md)
- [`../../architecture/pipeline-event-envelope.md`](../../architecture/pipeline-event-envelope.md)
- Phase 1 fixture code and Phase 2 raw-event plan artifacts.

Autoplan mode:

- CEO review: sequencing, wedge value, and phase boundary.
- Design review: skipped because Phase 3 has no UI.
- Engineering review: data flow, idempotency, event contracts, and tests.
- DX review: local fixture/debug workflow.

## Executive Verdict

Phase 3 is approved for implementation if it stays focused on normalized source
objects/files and deterministic relationship seeds. The plan should not leak
into chunking, retrieval, or real connector behavior.

The decisive invariant is that Phase 4 can chunk source objects and files
without reading provider-shaped raw payloads.

## CEO Review

Score: 8/10.

| Premise | Verdict | Reasoning |
| --- | --- | --- |
| Provider-shaped raw events should normalize before chunking. | Accepted | This protects downstream stages from provider-specific shape drift. |
| Fixture normalizers are enough before live connectors. | Accepted | They prove the contract and deterministic replay without OAuth scope. |
| Source files should be first-class now. | Accepted | The COR-123 diagram/OCR story requires file metadata to survive. |
| Relationship seeds belong in Phase 3. | Accepted with constraint | Deterministic seeds are useful; graph expansion and ranking are later work. |

Scope decisions:

- Add source object/file persistence now.
- Reuse Phase 2 raw-event pointer loading.
- Keep real provider connectors out.
- Keep chunking/OCR/indexing out.
- Persist fixture OCR text on source files for Phase 4, but keep OCR worker
  execution out.
- Publish pointer-only source object/file events after durable writes.

## Engineering Review

Score: 8/10.

```txt
raw_event.persisted
  -> NormalizationWorker.handle_raw_event_persisted
      -> RawEventRepository
      -> PayloadStore
      -> FixtureNormalizer
      -> SourceObjectRepository
      -> SourceFileRepository
      -> RelationshipSeedRepository
      -> source_object.upserted / source_file.fetched
```

Key decisions:

1. Source IDs must be deterministic.
   Decision: derive IDs from workspace/provider/object type/external ID.
2. No-op replay must be explicit.
   Decision: compare content hash and normalized version.
3. File metadata can leak sensitive data.
   Decision: hash filenames and keep content/OCR out of event payloads/logs.
4. Relationship seeds can overgrow into a graph service.
   Decision: keep only deterministic seeds required by fixtures.
5. Source connection FK can over-expand scope.
   Decision: use indexed string until connector tables exist.

## DX Review

Score: 8/10.

The local loop should stay:

```txt
pytest tests/normalization tests/workers tests/dev
alembic upgrade head
```

The plan is implementable if tests can build durable raw events from fixture
payloads without real provider credentials or live Kafka.

## Risks

| Risk | Mitigation |
| --- | --- |
| Provider-specific fields leak into Phase 4 contracts. | DTO tests and golden normalized records. |
| Source text/OCR leaks into event payloads or logs. | Envelope forbidden-key and logging/redaction tests. |
| Normalization replay republishes unchanged objects. | No-op tests by content hash and normalized version. |
| Relationship seed scope expands too far. | Keep graph ranking/link expansion out of Phase 3. |
| Fixture integration breaks Phase 1 workbench IDs. | Keep existing dev tests in focused loop. |

## Final Approval Gate

Approved to implement if:

- Phase 3 consumes Phase 2 raw events by pointer,
- source object/file writes are durable before events publish,
- unchanged replay no-ops,
- changed content or normalizer version republishes,
- downstream events carry only IDs, hashes, versions, and small metadata.
