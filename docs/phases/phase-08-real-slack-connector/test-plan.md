# Phase 8 Test Plan

## Commands

```bash
ruff check .
ruff format --check .
mypy src
pytest
```

Focused local loop:

```bash
pytest tests/connectors/slack tests/api/test_slack_oauth.py tests/api/test_slack_webhooks.py tests/retrieval tests/context_gate
```

## Coverage Map

```txt
OAuth
  -> state validation
  -> code exchange
  -> required scopes
  -> SecretRef storage
  -> reauth/scope drift

Source selection
  -> selected channels
  -> channel rename
  -> paused/disabled connection
  -> unselected event exclusion

Backfill
  -> channel history
  -> thread replies
  -> files/links
  -> pagination
  -> rate limits
  -> cursor resume
  -> retry/deadletter

Webhooks
  -> signature verification
  -> URL challenge
  -> retry dedupe
  -> message created/changed/deleted
  -> file shared/link shared/thread reply
  -> unsupported event safe ack

Pipeline integration
  -> raw_event.persisted envelope
  -> replay to Slack source objects/files
  -> retrieval/evidence pack
  -> context gate

Security
  -> no tokens in responses/logs/events
  -> no message text/file names/private URLs in event payloads
  -> unselected content does not leak
```

## Tests To Create

| Test file | Assertions |
| --- | --- |
| `tests/connectors/slack/test_oauth_service.py` | State validation, required scopes, SecretRef creation, reauth preserves install identity. |
| `tests/connectors/slack/test_source_selection.py` | Selected channels create source connections; unselected channels are excluded safely. |
| `tests/connectors/slack/test_backfill_service.py` | History pagination, thread reply fetch, raw-event persistence, idempotency keys. |
| `tests/connectors/slack/test_provider_cursor.py` | Cursor advances only after persistence; resume avoids duplicates. |
| `tests/connectors/slack/test_rate_limits_retries.py` | Slack rate limits retry with backoff; permanent failures deadletter. |
| `tests/connectors/slack/test_webhook_service.py` | Signature verification, URL challenge, duplicate retry no-op, supported event mapping. |
| `tests/connectors/slack/test_file_ingestion.py` | File metadata capture, allowed download, expired URL handling, OCR candidate routing. |
| `tests/connectors/slack/test_health.py` | OAuth health, scope drift, lag, cursor freshness, deadletter counts. |
| `tests/connectors/slack/test_redaction.py` | Tokens, message text, file names, private URLs, and raw snippets are absent from logs/events/responses. |
| `tests/api/test_slack_oauth.py` | OAuth route success/error shape with redaction. |
| `tests/api/test_slack_webhooks.py` | Slack webhook route verification, challenge, dedupe, and raw-event creation. |
| `tests/pipeline/test_slack_raw_event_replay.py` | Real-shaped Slack raw events replay into existing Slack source objects/files. |

## Golden Slack Fixture Assertions

Backfill message:

```json
{
  "provider": "slack",
  "event_type": "message",
  "source_connection_id": "srcconn_...",
  "raw_event_status": "persisted"
}
```

Webhook duplicate:

```json
{
  "webhook_delivery_status": "ignored_duplicate",
  "raw_event_created": false
}
```

Cursor resume:

```json
{
  "cursor_status": "active",
  "duplicates": 0,
  "last_persisted_event_ts": "..."
}
```

Retrieval/gate:

```json
{
  "source": "slack",
  "evidence_pack_contains_slack_citation": true,
  "context_gate_status": "allow_or_warn_or_block"
}
```

## Redaction Assertions

Search captured logs, event payloads, API responses, and health responses for:

- OAuth access token,
- refresh token,
- Slack signing secret,
- OAuth authorization code,
- OAuth state,
- message text,
- private channel name,
- file name,
- file private URL,
- raw Slack payload snippet.

All must be absent except where explicitly stored behind the raw payload/object
storage boundary and referenced by pointer.

## Not Required In Phase 8

- Real Linear/GitHub/repo-doc connectors,
- Slack approval bot,
- web connector admin polish,
- user-level Slack ACL snapshots,
- Enterprise Grid completeness,
- arbitrary external URL crawling,
- deep vision-model diagram understanding.
