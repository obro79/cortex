# Phase 8.5 Review Report

Date: 2026-05-08

Decision: `UNBLOCKED_FOR_PHASE_9`

## Scope

Reviewed Phase 8 Slack connector work through:

- `5503498 Implement offline Slack connector foundation`
- `fbc1c76 Implement live Slack OAuth and API client`

Covered:

- OAuth install and secret boundary
- Slack Web API client
- source selection
- backfill/cursors
- Events API webhook verification and dedupe
- file/link metadata redaction
- health
- automated tests
- manual live-dev Slack/ngrok run

## Commands Run

```bash
.venv/bin/pytest tests/connectors/slack tests/api/test_slack_oauth.py tests/api/test_slack_webhooks.py tests/retrieval tests/context_gate
.venv/bin/pytest
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/mypy src
```

Manual commands also exercised:

```bash
uvicorn cortex.api.app:app --host 127.0.0.1 --port 8000
ngrok http 8000
curl /connectors/slack/sources/channels
curl /connectors/slack/sources/select
curl /connectors/slack/backfill/{source_connection_id}
curl /connectors/slack/health/T0B28NBQL1Z
```

## Manual Evidence

See:

- [`2026-05-08-data-flow-map.md`](2026-05-08-data-flow-map.md)
- [`2026-05-08-manual-walkthrough.md`](2026-05-08-manual-walkthrough.md)
- [`2026-05-08-redaction-and-failure-drills.md`](2026-05-08-redaction-and-failure-drills.md)

Confirmed live:

- Slack OAuth install completed with active installation.
- Slack channel listing worked with the live token.
- Selected channel `#all-cortex-test` was backfilled.
- Backfill completed with raw events and cursor.
- Slack Event Subscriptions delivered a real `message.channels` POST through
  ngrok.
- Cortex verified the Slack signature and persisted the webhook raw event.
- Health showed active OAuth, one selected channel, one cursor, and no
  deadletters/retries.

## Fixes Made In Phase 8.5

- `SlackHealthService.workspace_health` now derives OAuth status from workspace
  installation records instead of always returning `active`.
- Added focused health test coverage for `needs_reauth`.
- Added `slack-normalizer-v1` for live-shaped Slack message payloads.
- Registered provider `slack` to the Slack normalizer instead of the fixture
  normalizer.
- Added Slack-aware chunking that indexes selected-channel message text with a
  content-free `Slack thread` citation label and no message text in chunk
  metadata.
- Exposed the Slack connector payload store to local pipeline services so
  raw-event persistence can feed normalization in tests.
- Added a deterministic embedding worker skeleton that consumes
  `source_chunk.upserted`, queues `embedding.requested`, and completes
  `embedding.completed` without Gemini.
- Added `InMemoryPipelineDispatcher` and wired Slack webhook/backfill routes to
  drain raw-event, source-object, chunk, and deterministic embedding events
  after successful intake.
- Added live-shaped Slack retrieval/context-gate tests proving selected-channel
  webhook payloads can become embedded evidence without copying Slack text into
  pipeline event payloads.

## Former Blocking Finding

### P1: Live Slack Data Is Not Yet In Retrieval/Gate

Status: fixed for Phase 8.5 validation.

Live-shaped Slack payloads now reach source objects, chunks, deterministic
embedding records, retrieval evidence, and context-gate inputs through the local
deterministic retrieval stack. Gemini embedding support remains out of scope for
this phase.

Validation added:

```bash
.venv/bin/pytest tests/normalization/test_slack_normalizer.py tests/chunking/test_source_aware_chunker.py tests/connectors/slack/test_live_retrieval_gate.py tests/connectors/slack/test_webhook_service.py tests/connectors/slack/test_backfill_service.py tests/retrieval/test_retrieval_service.py tests/context_gate/test_decision_engine.py
.venv/bin/pytest tests/workers/test_embedding_worker.py tests/connectors/slack/test_live_retrieval_gate.py tests/embeddings/test_embedding_service.py
.venv/bin/pytest tests/api/test_slack_webhooks.py tests/workers/test_embedding_worker.py
.venv/bin/pytest
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/mypy src
```

## Non-Blocking Findings

- Phase 8 connector state is in memory for local testing. This is acceptable for
  the current skeleton but must move to database-backed repositories before any
  durable multi-process or hosted testing.
- Event Subscriptions currently require manual ngrok URL setup. This is
  acceptable for local dev but should become documented setup or a CLI helper.

## Redaction Result

PASS for committed artifacts and API responses reviewed.

No Slack access token, signing secret, client secret, OAuth code/state, raw Slack
payload, private file URL, or message text is committed in Phase 8.5 run logs.
New tests also assert Slack message text, private file names, private file URLs,
and private link URLs are absent from pipeline event payloads.

## Final Decision

`UNBLOCKED_FOR_PHASE_9`

Phase 9 may start from the Phase 8.5 data-path perspective. The connector is
proven live through raw events, and live-shaped Slack payloads are now proven
through automatic deterministic embedding, retrieval, and context gate locally.
Residual risk: the external Slack/ngrok manual walkthrough was not re-run after
this code change, so hosted or manual live-dev verification should still be
repeated before treating this as production-ready.
