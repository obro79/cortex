# Phase 8.5 Kafka Slack E2E Smoke

Date: 2026-05-08

Mode: local Apache Kafka broker plus local Postgres state.

This smoke used a synthetic live-shaped Slack message payload so no Slack token,
signing secret, OAuth code/state, raw Slack payload from a real workspace,
private URL, or selected-channel message text is committed here.

## Purpose

Prove the Phase 8.5 path can run across durable infrastructure:

1. Persist a selected-channel Slack-shaped raw event.
2. Publish a pointer-only `raw_event.persisted` event to Kafka.
3. Consume through the Kafka worker.
4. Normalize into a Slack source object.
5. Chunk into retrievable Slack text.
6. Produce a deterministic embedding row without Gemini.

## Commands

```bash
docker compose up -d postgres kafka
DATABASE_URL=postgresql+asyncpg://cortex:cortex@localhost:5432/cortex .venv/bin/alembic upgrade head
DATABASE_URL=postgresql+asyncpg://cortex:cortex@localhost:5432/cortex KAFKA_BOOTSTRAP_SERVERS=localhost:29092 PAYLOAD_STORE_PATH=.local/kafka-smoke-payloads .venv/bin/python scripts/kafka_slack_e2e_smoke.py
```

Focused and full validation after the Kafka fix:

```bash
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/mypy src
.venv/bin/pytest
docker compose config
git diff --check
```

## Result

```json
{"channel_id": "C_KAFKA_SMOKE", "counts": {"embeddings": 1, "raw_events": 1, "source_chunks": 1, "source_objects": 1}, "ok": true, "workspace_id": "ws_kafka_smoke_1778276410"}
```

Full test suite result from the same closeout pass: `198 passed`.

## What This Proves

- Slack-shaped selected-channel intake reaches the raw event store.
- Kafka payloads stay pointer-only and do not carry Slack message text.
- The Kafka consumer drains normalization, chunking, and deterministic embedding
  work against durable SQL state.
- Gemini is not required for Phase 8.5 validation.

## Remaining Boundary

This smoke does not replace the prior external Slack/ngrok manual walkthrough.
It proves the durable local Kafka/Postgres data path with live-shaped Slack
payloads, not production hosted Slack delivery.
