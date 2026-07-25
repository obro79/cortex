# Phase 2 Follow-Up Plan: Durable Kafka E2E Pipeline

## Goal

Finish the real Apache Kafka path for Phase 2 by proving that a Slack-shaped
event can cross process boundaries:

```txt
Slack webhook/backfill payload
  -> raw object store payload_ref
  -> raw_events row
  -> Kafka raw_event.persisted
  -> pipeline worker consumer
  -> normalization
  -> source_objects/source_files/relationships rows
  -> Kafka source_object/source_file events
  -> chunking
  -> source_chunks rows
  -> Kafka embedding.requested
  -> deterministic embedding worker
  -> embedding_records row
  -> Kafka embedding.completed
```

Kafka remains content-free. Raw Slack text may exist in the selected-source
payload store and retrieval chunks because retrieval needs it, but Kafka
payloads, deadletters, health endpoints, and logs must only carry pointers,
hashes, IDs, counts, and safe metadata.

## Current State

Already done:

- Apache Kafka is the local broker in `docker-compose.yml` using KRaft mode.
- `KafkaEventBus` publishes pointer-only `PipelineEventEnvelope` messages.
- `KafkaPipelineConsumer` can consume messages, dispatch them, commit offsets,
  and publish content-free deadletters.
- `CORTEX_STATE_BACKEND=memory|sql` separates state storage from event-bus
  choice, and `CORTEX_EVENT_BUS=kafka` requires SQL state.
- `CORTEX_CONFIG_FILE` can load YAML profiles such as `config/kafka-local.yaml`;
  env vars and explicit constructor settings still override YAML.
- Slack live payloads normalize to `slack_thread` source objects.
- Slack chunks can be retrieved and used by the context gate with deterministic
  embeddings in in-memory tests.

Still missing:

- `cortex-worker --role pipeline` now has the durable consumer path.
- `scripts/kafka_slack_e2e_smoke.py` proves live Apache Kafka plus Postgres can
  ingest a selected Slack message, consume through the pipeline worker stack,
  and create durable raw event, source object, chunk, and embedding rows.
- API Kafka mode now persists raw events through SQL, but Slack connector
  install/source-selection state is still process-local.
- SQL source object, file, relationship, chunk, and embedding repositories still
  need normal pytest integration coverage, not only the standalone smoke.
- Slack connector install/source-selection state is still process-local for the
  smoke path.

## Non-Goals

- No Gemini API or Gemini embeddings.
- No Redpanda.
- No hosted Kafka deployment work.
- No exactly-once semantics beyond idempotent durable writes plus manual offset
  commit after handler success/deadletter.
- No Qdrant requirement; deterministic embeddings and FTS retrieval are enough
  for this phase.
- No production OAuth/source install persistence unless local Kafka E2E is
  blocked by the current Slack service factory.

## Implementation Plan

### 1. Add Durable Derived-State Repositories

Add SQLAlchemy-backed repositories that match the current in-memory repository
surface area:

- `src/cortex/normalization/repositories.py`
  - `SqlAlchemySourceObjectRepository`
  - `SqlAlchemySourceFileRepository`
  - `SqlAlchemyRelationshipSeedRepository`
- `src/cortex/chunking/repositories.py`
  - `SqlAlchemySourceChunkRepository`
- `src/cortex/embeddings/repositories.py`
  - `SqlAlchemyEmbeddingRecordRepository`

Keep current in-memory repositories for unit tests and API local mode. Do not
change service behavior more than needed; adapt the durable repositories to the
existing service method names first.

Acceptance:

- Upserts are idempotent by the same external identity/content hash rules as
  in-memory repositories.
- Duplicate Slack event replay does not create duplicate source chunks or
  embedding records.
- Repository methods return contract DTOs, not SQLAlchemy model instances.

### 2. Build the Durable Pipeline Factory

Add a worker factory module, for example `src/cortex/workers/factory.py`, that
creates one complete pipeline stack from settings:

- SQLAlchemy session/sessionmaker.
- `FilePayloadStore` rooted at `PAYLOAD_STORE_PATH`.
- `SqlAlchemyRawEventRepository`.
- SQL source object, file, relationship, chunk, and embedding repositories.
- `KafkaEventBus` for downstream publication.
- `SourceNormalizationService`, `ChunkingService`, `EmbeddingService`, and
  `EmbeddingWorkerSkeleton`.
- `KafkaPipelineConsumer`.

The factory should make dependency ownership explicit so tests can inject fake
sessions, fake Kafka clients, and temporary payload stores.

Acceptance:

- The factory can be built without `GEMINI_API_KEY`.
- It uses deterministic embeddings from config for this phase.
- It does not log raw payload bytes or Slack text during construction or
  handling.

### 3. Make `cortex-worker --role pipeline` Run Kafka

Update `src/cortex/workers/main.py`:

- `noop` keeps returning immediately.
- `pipeline` provisions Kafka topics, builds the durable pipeline consumer, and
  runs `run_forever(...)` on pipeline topics.
- Shutdown should call consumer/producer stop methods from `finally`.

Acceptance:

- `uv run cortex-worker --role pipeline` stays alive and consumes Kafka
  messages.
- Worker startup fails fast with a clear message when required Kafka settings
  are missing.
- A focused test verifies that the pipeline role calls the consumer loop instead
  of only provisioning topics.

### 4. Wire API Kafka Mode to Durable Raw Events

Keep local in-memory mode for tests/dev, but when `CORTEX_EVENT_BUS=kafka`:

- Use `KafkaEventBus` for raw-event publication.
- Store raw payload bytes through `FilePayloadStore`.
- Persist `raw_events` through `SqlAlchemyRawEventRepository`.
- Return API responses that expose counts and IDs only, not Slack message text.

If connector installation/source selection persistence is still in-memory, keep
the E2E smoke path scoped to a running API process with selected channels
configured during the test. Only add durable Slack connector repositories if the
smoke path cannot be made reliable without them.

Acceptance:

- A selected Slack channel message creates a durable raw event and Kafka
  `raw_event.persisted` message.
- An unselected Slack channel is ignored before raw-event persistence and Kafka
  publication.
- Pipeline event payloads remain pointer-only.

### 5. Preserve Kafka Content Boundaries

Add a shared assertion helper for Kafka envelopes/deadletters that rejects:

- Slack message text.
- Raw provider payload JSON.
- OAuth tokens or secret refs.
- Private file URLs.
- Raw Slack file metadata.

Apply it to producer, consumer, deadletter, and E2E tests.

Acceptance:

- Invalid envelopes deadletter without including original message bytes.
- Handler failures deadletter with event IDs and error classes only.
- `git diff` and committed docs/run logs contain no secrets or private Slack
  content.

### 6. Add Kafka E2E Validation

Add a narrow E2E test or smoke script, guarded so normal unit tests do not
require Docker:

- `tests/integration/test_kafka_slack_pipeline_e2e.py`, or
- `scripts/kafka_slack_e2e_smoke.py` plus a pytest wrapper.

Flow:

1. Start Postgres and Apache Kafka from compose.
2. Apply migrations.
3. Start API dependencies in Kafka mode, or call the same ingestion service
   factory the API uses.
4. Send a signed Slack message event for a selected channel.
5. Confirm `raw_events` row and payload object exist.
6. Confirm `raw_event.persisted` is consumed by the worker.
7. Confirm source object, source chunk, and embedding record rows exist.
8. Confirm retrieval can return the Slack chunk for a matching query.
9. Confirm Kafka messages and deadletters do not contain Slack text.

Acceptance:

- The smoke command exits non-zero on timeout or missing durable writes.
- The smoke command prints only IDs, counts, hashes, and statuses.
- The test can run with deterministic embeddings and no external AI API keys.

## Test Plan

Focused unit tests:

- SQL repository parity with in-memory repository behavior.
- Kafka pipeline role starts the consumer loop.
- API Kafka mode persists payload refs and publishes `raw_event.persisted`.
- Kafka deadletters are content-free for invalid JSON and handler failures.
- Duplicate Slack event replay is idempotent through chunks and embeddings.

Focused integration tests:

- Slack-shaped event to durable raw event to Kafka producer.
- Kafka consumer to normalization/chunking/embedding durable writes.
- Retrieval/context gate can use the resulting Slack evidence.

Manual smoke:

```bash
docker compose up -d postgres kafka
DATABASE_URL=postgresql+asyncpg://cortex:cortex@localhost:5432/cortex \
  uv run alembic upgrade head
DATABASE_URL=postgresql+asyncpg://cortex:cortex@localhost:5432/cortex \
  KAFKA_BOOTSTRAP_SERVERS=localhost:29092 \
  PAYLOAD_STORE_PATH=.local/kafka-smoke-payloads \
  uv run python scripts/kafka_slack_e2e_smoke.py
```

Expected output is content-free JSON with IDs/counts only, for example:

```json
{"channel_id":"C_KAFKA_SMOKE","counts":{"embeddings":1,"raw_events":1,"source_chunks":1,"source_objects":1},"ok":true,"workspace_id":"ws_kafka_smoke_..."}
```

Final validation before commit:

```bash
uv run pytest tests/events tests/workers tests/ingestion tests/normalization tests/chunking tests/embeddings tests/connectors/slack
uv run pytest tests/integration/test_kafka_slack_pipeline_e2e.py
uv run ruff check .
uv run ruff format --check .
uv run mypy src
docker compose config
git diff --check
```

## Suggested Patch Order

1. Durable repository implementations and parity tests.
2. Worker factory and `cortex-worker --role pipeline` consumer loop.
3. API Kafka-mode raw event/payload store wiring.
4. Content-boundary test helper and deadletter coverage.
5. Kafka Slack E2E smoke test and docs.

This order keeps the riskiest cross-process change blocked behind durable state
instead of adding a real consumer that still depends on process-local memory.

## Open Decisions

- Whether the E2E test should run as a pytest integration test only, or also as
  a standalone script for demos.
- Whether Slack source selection persistence should be pulled into this patch or
  left as a connector follow-up after the Kafka path proves durable.
- Whether offset commits should happen after every message, as today, or in
  small batches after the E2E path is stable.
