# Phase 8 Autoplan Review

## Review Scope

Plan reviewed:

- [`plan.md`](plan.md)
- [`implementation-checklist.md`](implementation-checklist.md)
- [`test-plan.md`](test-plan.md)
- Phase 8 roadmap,
- connector/security architecture docs,
- Slack file/OCR ADR,
- Phase 2 raw-event plan,
- Phase 3 normalization plan,
- Phase 5 retrieval plan,
- Phase 6 context-gate plan.

Autoplan mode:

- CEO review: production wedge and trust value.
- Design review: skipped because Phase 8 has no customer UI beyond minimal
  connector routes.
- Engineering review: OAuth, cursors, webhooks, backfill, retries, redaction,
  replay.
- DX review: local Slack fixture parity and focused test loop.

## Executive Verdict

Phase 8 is approved if real Slack remains a connector into the existing
raw-event spine. Do not build a second Slack-specific retrieval or memory path.

## CEO Review

Score: 9/10.

| Premise | Verdict | Reasoning |
| --- | --- | --- |
| Slack should be the first real connector. | Accepted | Slack is the wedge where decisions and diagrams live. |
| Selected-channel source allowlists are enough for v1. | Accepted | User-level ACL snapshots can wait, but channel boundaries must be strict. |
| Real Slack must feed the existing pipeline. | Accepted | This proves production shape without discarding fixture work. |
| Web/admin polish can wait. | Accepted | OAuth/source-selection API plus health is enough to validate the connector. |

## Engineering Review

Score: 8/10.

```txt
OAuth install
  -> source connection
  -> backfill/webhook
  -> raw event
  -> replay/normalize
  -> retrieval/gate
```

Key decisions:

1. Token material lives only behind `SecretRef`.
2. Cursors advance only after durable raw-event persistence or duplicate no-op.
3. Webhook verification happens before payload processing.
4. Unselected-channel events do not leak content.
5. Slack real events reuse the same normalizers as Slack fixture events.
6. Event envelopes stay pointer-only and content-free.

## DX Review

Score: 8/10.

The local loop should be:

```txt
pytest tests/connectors/slack tests/api/test_slack_webhooks.py tests/pipeline/test_slack_raw_event_replay.py
```

Implementation should rely on recorded Slack-shaped fixtures for repeatable
tests. Live Slack API calls belong in optional/manual smoke tests with redacted
output.

## Risks

| Risk | Mitigation |
| --- | --- |
| Tokens leak through logs or API responses. | SecretRef boundary plus redaction tests. |
| Webhook spoofing creates raw events. | Signature/timestamp verification before processing. |
| Cursor advances before persistence. | Cursor advancement rule and resume tests. |
| Unselected channels leak metadata/content. | Channel allowlist enforcement and exclusion tests. |
| Backfill and webhooks duplicate messages. | Provider idempotency keys and duplicate no-op paths. |
| Slack-specific path bypasses retrieval/gate safety. | Reuse raw-event normalization and existing retrieval/gate tools. |

## Final Approval Gate

Approved to implement if:

- Slack OAuth install stores token material only through `SecretRef`,
- selected channels define the v1 source boundary,
- backfill and webhooks persist raw events through the existing pipeline,
- cursors and retries are replay-safe,
- real Slack data reaches retrieval/gate through the same path as fixtures,
- logs/events/responses do not expose Slack secrets or content.
