# Phase 8.5 Manual Slack Walkthrough

Date: 2026-05-08

Mode: live-dev workspace, selected public test channel only.

Workspace/app identifiers are recorded only where they are non-secret. Slack
token material, signing secret, client secret, OAuth authorization code, OAuth
state, and raw Slack payloads are intentionally omitted.

## Environment

- Branch: `main`
- Reviewed head: `fbc1c76`
- Local API: `http://127.0.0.1:8000`
- ngrok HTTPS tunnel: temporary `ngrok-free.dev` URL
- Slack workspace: `T0B28NBQL1Z`
- Selected test channel: `#all-cortex-test`
- Selected channel ID: `C0B2F400FS6`
- OAuth installation ID observed during run: `oauth_6c0a782b10ff5b348924944e`
- Source connection ID observed during run: `srcconn_03e3f02d00d3630806660f83`

## Steps And Evidence

1. Started local Cortex API with Slack connector configuration.
   - Result: API served Slack OAuth and connector routes on port 8000.

2. Started ngrok for Slack Event Subscriptions.
   - Result: public HTTPS tunnel forwarded to local port 8000.

3. Completed Slack OAuth install.
   - Result: OAuth response was `ok: true`, installation `status: active`,
     `missing_scopes: []`, and bot user ID present.
   - Secret ref metadata was returned; token material was not returned.

4. Listed Slack channels through Cortex.
   - Result: `#all-cortex-test` appeared with `is_member: true` after the bot was
     invited.
   - One intentionally unselected public channel also appeared and was not
     selected.

5. Selected `#all-cortex-test`.
   - Result: `SourceConnection` created with the channel ID and a hashed display
     name.

6. Ran selected-channel backfill.
   - Command shape:
     `POST /connectors/slack/backfill/{source_connection_id}`
   - Result:
     - `ok: true`
     - job `status: completed`
     - `raw_events_created: 5`
     - `duplicates: 0`
     - cursor set to Slack timestamp high watermark

7. Enabled Slack Event Subscriptions and subscribed bot events.
   - Request URL verified by Slack.
   - Events configured:
     - `message.channels`
     - `file_created`
     - `link_shared`
     - `file_shared`
   - App was reinstalled after scope/event changes.

8. Sent a fresh message in `#all-cortex-test`.
   - ngrok observed Slackbot `POST /connectors/slack/events?...`.
   - Cortex response:
     - `200 OK`
     - `ok: true`
     - `status: persisted`
     - `raw_event_created: true`

9. Checked connector health.
   - Result:
     - `oauth_status: active`
     - `selected_channel_count: 1`
     - `cursor_count: 1`
     - `deadletter_count: 0`
     - `retrying_count: 0`

10. Checked dev workbench separately.
    - Enabled local `CORTEX_DEV_WORKBENCH_ENABLED=true`.
    - `/dev/workbench` returned `200`.
    - Deterministic COR-123 evals passed with `actual_gate: block`.

## Manual Result

Live Slack install, selected-channel backfill, Event Subscriptions delivery,
signature verification, and raw-event persistence are confirmed.

Live Slack retrieval and context-gate confirmation are not complete because live
Slack raw events are not yet normalized into source objects/chunks/indexes.
