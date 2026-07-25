# Phase 8.5 Review Report

Date: 2026-05-08

Decision: `BLOCKED`

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

## Blocking Findings

### P1: Live Slack Data Is Not Yet In Retrieval/Gate

Live Slack payloads reach raw-event persistence, but provider `"slack"` still
uses the fixture normalizer path. There is no dedicated live Slack
normalizer/chunker/index path that produces source objects, source files,
chunks, retrieval evidence, and context-gate inputs from live Slack raw events.

Required remediation:

1. Add a live Slack normalizer for message/thread/file/link raw events.
2. Route live Slack source objects/source files into chunking and indexing.
3. Add replay tests for live-shaped Slack raw events.
4. Add retrieval/evidence/context-gate tests showing live-shaped Slack evidence.
5. Repeat Phase 8.5 retrieval/gate manual confirmation.

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

## Final Decision

`BLOCKED`

Phase 9 should wait. The connector is proven live through raw events, but Phase
8 completion criteria and Phase 8.5 approval threshold require real Slack data
to reach retrieval and context gate. That path remains unimplemented for live
Slack payloads.
