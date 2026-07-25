# Phase 8.5 Data-Flow Map

Date: 2026-05-08

Reviewed commits:

- `5503498 Implement offline Slack connector foundation`
- `fbc1c76 Implement live Slack OAuth and API client`

## Summary

The live Slack connector now reaches the raw-event boundary through OAuth,
source selection, backfill, and Slack Events API webhooks. Live Slack data does
not yet reach production source objects, chunks, retrieval, or context gate.
Those downstream paths still depend on deterministic fixture normalizers and
fixture retrieval.

## Edges

| Edge | Code path | Record/event | Idempotency | Redaction boundary | Failure behavior | Test coverage |
| --- | --- | --- | --- | --- | --- | --- |
| OAuth start | `SlackOAuthService.start_install` | in-memory OAuth state | generated state | state is returned only to caller; not logged by service | invalid/missing callback state rejected | `tests/connectors/slack/test_oauth_service.py`, `tests/api/test_slack_oauth.py` |
| OAuth callback | `RealSlackOAuthClient.exchange_code` -> `SlackOAuthService.complete_install` | `OAuthInstallation`, `SecretRef` | workspace/provider workspace upsert | token material stored behind `SecretRef`; API response returns secret ref metadata only | Slack OAuth errors return `oauth_exchange_failed`; missing scopes mark `needs_reauth` | `tests/connectors/slack/test_live_clients.py`, `tests/connectors/slack/test_oauth_service.py` |
| Channel listing | `SlackSourceSelectionService.list_channels` -> `RealSlackWebClient.conversations_list` | channel summary response | Slack cursor | uses bearer token internally; no token in response | Slack API error raises provider error | `tests/connectors/slack/test_live_clients.py`, `tests/connectors/slack/test_source_selection.py` |
| Source selection | `SlackSourceSelectionService.select_channels` | `SourceConnection` | workspace/provider/channel upsert | channel display name is hashed on persisted connection | unknown installation raises lookup error | `tests/connectors/slack/test_source_selection.py`, `tests/api/test_slack_oauth.py` |
| Backfill | `SlackBackfillService.backfill_source` -> `RealSlackWebClient.conversation_history` | `BackfillJob`, `RawEvent`, `raw_event.persisted`, `ProviderCursor` | per Slack event idempotency key | pipeline event payload is pointer-only; raw payload boundary still stores Slack payload | rate limits mark retrying; permanent provider errors deadletter | `tests/connectors/slack/test_backfill_service.py`, `tests/connectors/slack/test_provider_cursor.py` |
| Files/links from backfill | `derived_raw_events_for_message` | `RawEvent` with `file_shared` / `link_shared` | message/file/link derived keys | file names/private URLs are removed; hashes/metadata remain | bad metadata does not block base message event construction | `tests/connectors/slack/test_file_ingestion.py` |
| Webhook verification | `SlackWebhookVerifier.verify` -> `SlackWebhookService.handle` | `WebhookDelivery`, optional `RawEvent` | provider event id / delivery id | verification happens before payload processing | bad signature or stale timestamp rejects before persistence | `tests/connectors/slack/test_webhook_service.py`, `tests/api/test_slack_webhooks.py` |
| Webhook selected-channel intake | `SlackWebhookService.handle` | `WebhookDelivery`, `RawEvent`, `raw_event.persisted` | Slack event id; duplicate delivery no-ops | selected-channel event is persisted only after allowlist lookup; API response is content-free | unselected channel returns `ignored_unselected`; unsupported event returns `ignored` | `tests/connectors/slack/test_webhook_service.py` |
| Replay | `RawEventReplayService.replay_by_id` | `raw_event.persisted` replay envelope | raw event id | event envelope remains pointer-only | deleted raw events cannot replay | `tests/ingestion/test_raw_event_replay.py` |
| Normalization | `NormalizerRegistry.resolve` | `SourceObject`, `SourceFile`, relationship seeds | provider/external object identity | fixture normalizer redacts content from metadata | unsupported or malformed payload can deadletter | `tests/normalization/*`, `tests/workers/test_normalization_worker.py` |
| Retrieval/gate | `cortex.dev` fixtures, retrieval, context gate services | `EvidencePack`, `ContextGateResult` | deterministic fixture IDs | fixture citation output is content-safe | fixture gate blocks stale Redis-vs-Postgres conflict | `tests/retrieval/*`, `tests/context_gate/*`, `tests/dev/*` |

## Blocking Gap

The Slack provider is currently registered to the fixture normalizer path:
`NormalizerRegistry` maps `"slack"` to `normalize_fixture_payload`. Live Slack
raw payloads do not yet have a dedicated normalizer/chunker/index path, so live
Slack data cannot be manually confirmed in production retrieval or context gate.

Phase 9 should not start until this is fixed or explicitly descoped into a
Phase 8 follow-up.
