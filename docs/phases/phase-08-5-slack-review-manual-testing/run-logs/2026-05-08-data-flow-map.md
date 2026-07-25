# Phase 8.5 Data-Flow Map

Date: 2026-05-08

Reviewed commits:

- `5503498 Implement offline Slack connector foundation`
- `fbc1c76 Implement live Slack OAuth and API client`

## Summary

The live Slack connector reaches the raw-event boundary through OAuth, source
selection, backfill, and Slack Events API webhooks. Live-shaped Slack message
payloads now continue through normalization, source-aware chunking, retrieval,
deterministic embedding, and context gate using deterministic embeddings plus
FTS. Gemini is not required for Phase 8.5 validation.

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
| Webhook selected-channel intake | `SlackWebhookService.handle` -> `InMemoryPipelineDispatcher.drain` | `WebhookDelivery`, `RawEvent`, `raw_event.persisted`, downstream pipeline events | Slack event id; duplicate delivery no-ops | selected-channel event is persisted only after allowlist lookup; API response is content-free | unselected channel returns `ignored_unselected`; unsupported event returns `ignored` | `tests/connectors/slack/test_webhook_service.py`, `tests/api/test_slack_webhooks.py` |
| Backfill selected-channel intake | `SlackBackfillService.backfill_source` -> `InMemoryPipelineDispatcher.drain` | `BackfillJob`, `RawEvent`, `raw_event.persisted`, downstream pipeline events | per Slack event idempotency key | backfill API returns counts/cursor only, not message text | duplicates count without rewriting payloads | `tests/connectors/slack/test_backfill_service.py` |
| Replay | `RawEventReplayService.replay_by_id` | `raw_event.persisted` replay envelope | raw event id | event envelope remains pointer-only | deleted raw events cannot replay | `tests/ingestion/test_raw_event_replay.py` |
| Slack normalization | `normalize_slack_payload` via `NormalizerRegistry.resolve` | `SourceObject` with object type `slack_thread` | workspace/team/channel/thread/message timestamp | source object `content_text` stores Slack message text only as retrieval input; metadata keeps channel id/hash, user id, timestamps, counts, and file/link flags | malformed message payload can deadletter; file/link-only events emit no source object | `tests/normalization/test_slack_normalizer.py`, `tests/connectors/slack/test_live_retrieval_gate.py` |
| Slack chunking | `SourceAwareChunker.chunks_for_source_object` | `SourceChunk` with type `slack_message` | source object/chunk type/index/version | chunk metadata omits message text; citation label is content-free `Slack thread` | duplicate replay noops existing chunks | `tests/chunking/test_source_aware_chunker.py`, `tests/connectors/slack/test_live_retrieval_gate.py` |
| Deterministic embedding | `EmbeddingWorkerSkeleton.handle_source_chunk_upserted` -> `EmbeddingService.queue_for_chunk` -> `EmbeddingWorkerSkeleton.handle_embedding_requested` | `EmbeddingRecord`, `embedding.requested`, `embedding.completed` | workspace/source chunk/embedding version | embedding events carry hashes/provider/model/dimensions only, not Slack text | duplicate chunk/version noops existing embedding request | `tests/workers/test_embedding_worker.py`, `tests/connectors/slack/test_live_retrieval_gate.py` |
| Retrieval/gate | `RetrievalService`, `ContextGateService` | `EvidencePack`, `ContextGateResult` | deterministic request/evidence/gate IDs | pipeline events remain pointer-only; Slack snippets appear only in retrieval evidence output | permission filters and gate failure behavior remain unchanged | `tests/retrieval/*`, `tests/context_gate/*`, `tests/connectors/slack/test_live_retrieval_gate.py` |

## Phase 8.5 Unblock Evidence

Added validation:

- live Slack message payload normalizes to a stable `slack_thread` source object,
- backfill-shaped Slack message payload normalizes through the same path,
- file/link-only Slack events do not emit private file URLs or raw file metadata,
- signed Slack webhook route automatically drains raw-event, source-object,
  chunk, and embedding events,
- selected-channel webhook raw event flows through normalization, chunking,
  deterministic embedding, retrieval, and context gate,
- duplicate replay does not create duplicate Slack chunks,
- pipeline event payloads remain content-free.

Remaining manual limitation: this update validates live-shaped payloads in the
local in-memory pipeline. It does not re-run the external Slack/ngrok manual
walkthrough from scratch.
