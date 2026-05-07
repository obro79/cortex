# Phase 8.5 Test Plan

## Automated Commands

Run the Phase 8 automated suite before manual review:

```bash
ruff check .
ruff format --check .
mypy src
pytest tests/connectors/slack tests/api/test_slack_oauth.py tests/api/test_slack_webhooks.py tests/retrieval tests/context_gate
```

Run the full suite if the focused suite passes:

```bash
pytest
```

## Manual Review Matrix

| Area | Check | Evidence |
| --- | --- | --- |
| OAuth | Install succeeds, state validated, tokens hidden. | Command output/API response/log search. |
| Source selection | Selected channel ingests; unselected channel excluded. | Source connection records and retrieval output. |
| Backfill | Messages/replies/files/links persist as raw events. | Raw event counts and replay evidence. |
| Webhooks | Signature verified, retries deduped, supported events persisted. | Webhook delivery records. |
| Cursors | Resume avoids skipped or duplicated events. | Cursor records before/after simulated crash. |
| Files | Metadata/OCR path works; failures do not block messages. | Source file records and failure logs. |
| Retrieval | Slack citation appears in evidence pack. | Evidence pack output. |
| Context gate | Slack evidence affects allow/warn/block output. | Gate result output. |
| Health | Lag, cursor freshness, OAuth health, deadletters visible. | Health response/screenshot. |
| Redaction | No tokens/content/private URLs leak. | Search results. |

## Visual Confirmation

Capture evidence for:

- connector health/source coverage,
- backfill progress or final status,
- webhook delivery status,
- evidence pack with Slack citation,
- context gate result using Slack evidence,
- deadletter/retry visibility if available.

Screenshots should be redacted before they are committed.

## Redaction Search Terms

Search all review artifacts and captured outputs for:

- actual Slack access token prefix/value,
- actual Slack signing secret,
- OAuth authorization code,
- OAuth state,
- test message text,
- private channel name,
- file name,
- private file URL,
- raw payload excerpt,
- unselected-channel message text.

Expected result: no hits outside raw payload/object-storage pointers.

## Failure Drills

| Drill | Expected behavior |
| --- | --- |
| Invalid signature | Request rejected; no raw event. |
| Stale timestamp | Request rejected; no raw event. |
| Duplicate webhook retry | Delivery marked duplicate; no second raw event. |
| Crash before cursor advance | Resume reprocesses safely; duplicate no-op if needed. |
| Rate limit | Backoff/retry; job remains resumable. |
| Permanent provider failure | Deadletter with repair pointer and no content leak. |
| Revoked token/scope drift | Connector unhealthy/needs reauth. |
| Unselected channel event | Acknowledged or excluded without content. |
| Downstream normalization failure | Raw event can replay. |

## Approval Threshold

Phase 8.5 can approve Phase 9 only if:

- focused automated tests pass,
- manual walkthrough succeeds,
- retrieval and gate are confirmed with Slack evidence,
- redaction audit passes,
- no P0/P1 review findings remain open,
- P2 findings are either fixed or explicitly accepted as Phase 9-safe.
