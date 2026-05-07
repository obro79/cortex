# Phase 8 Plan: Real Slack Connector

## Goal

Replace fixture Slack ingestion with the first real provider connector while
preserving the same pipeline shape:

```txt
Slack OAuth install
  -> source_connection(selected channels)
  -> backfill job and provider cursor
  -> Slack Web API / Events API
  -> webhook delivery or backfill item
  -> raw_event persisted
  -> raw_event.persisted
  -> existing Slack normalizer
  -> source objects/files/chunks
  -> retrieval/evidence/context gate/canonical memory
```

The invariant: real Slack data must enter Cortex as raw provider events and then
use the same downstream pipeline as fixture Slack data.

## Inputs

- [`../implementation-roadmap.md`](../implementation-roadmap.md#phase-8-real-slack-connector)
- [`../../architecture/handbook.md`](../../architecture/handbook.md)
- [`../../architecture/v1-entity-state-schema.md`](../../architecture/v1-entity-state-schema.md)
- [`../../architecture/pipeline-event-envelope.md`](../../architecture/pipeline-event-envelope.md)
- [`../../architecture/adrs/011-slack-files-diagrams-ocr/README.md`](../../architecture/adrs/011-slack-files-diagrams-ocr/README.md)
- [`../../architecture/adrs/012-secrets-token-management/README.md`](../../architecture/adrs/012-secrets-token-management/README.md)
- [`../phase-02-raw-event-pipeline/plan.md`](../phase-02-raw-event-pipeline/plan.md)
- [`../phase-03-normalization-source-objects/plan.md`](../phase-03-normalization-source-objects/plan.md)
- [`../phase-05-retrieval-evidence-packs/plan.md`](../phase-05-retrieval-evidence-packs/plan.md)
- [`../phase-06-context-gate/plan.md`](../phase-06-context-gate/plan.md)

## Existing Foundation

Earlier phases provide:

- raw event persistence and `raw_event.persisted` publication,
- Slack fixture normalizers for messages, threads, files, and OCR metadata,
- source objects, source files, chunks, embeddings, and indexes,
- retrieval/evidence packs,
- context gate and canonical-memory flows that consume retrieved Slack evidence,
- source allowlist concepts from retrieval and permission planning.

Phase 8 should replace only the Slack input side. It should not fork the
normalization or retrieval path for real Slack.

## Non-Goals

- No Linear, GitHub, or repo-docs real connectors.
- No Slack approval bot.
- No polished connector admin web UI beyond minimal install/source-selection
  endpoints needed for integration.
- No provider-native per-user ACL snapshots beyond selected-channel source
  allowlists.
- No enterprise Slack Grid deep support beyond storing team/workspace IDs in a
  way that does not block it later.
- No full retention/deletion implementation beyond respecting deletion events
  and not leaking deleted content through new connector logs/events.
- No deep vision-model diagram understanding; metadata plus OCR remains the v1
  file strategy.

## Architecture

```txt
SlackOAuthService
  -> start_install()
  -> complete_install(code/state)
  -> create OAuthInstallation(secret_ref, scopes, team metadata)

SlackSourceSelectionService
  -> list_available_channels()
  -> upsert SourceConnection(selected channel IDs)

SlackBackfillService
  -> create BackfillJob
  -> load SourceConnection and ProviderCursor
  -> fetch channel history and thread replies
  -> persist RawEvent for each message/file/link/delete/edit shape
  -> advance cursor only after durable raw-event persistence

SlackWebhookService
  -> verify Slack signature and timestamp
  -> handle URL verification challenge
  -> create WebhookDelivery
  -> dedupe by provider delivery/event ID
  -> persist RawEvent
  -> publish raw_event.persisted

SlackHealthService
  -> source coverage
  -> ingestion lag
  -> cursor freshness
  -> retry/deadletter counts
  -> OAuth/scope health
```

The connector boundary owns OAuth, selected sources, Slack API fetches, webhook
verification, provider cursors, retries, and health. The raw-event pipeline owns
payload storage, idempotency, replay, normalization, indexing, retrieval, and
gate behavior.

## Proposed Module Layout

```txt
src/cortex/connectors/
  __init__.py
  slack/
    __init__.py
    oauth.py
    client.py
    sources.py
    backfill.py
    webhooks.py
    cursors.py
    files.py
    health.py
    mapping.py
    service.py

tests/connectors/slack/
tests/api/test_slack_oauth.py
tests/api/test_slack_webhooks.py
```

Keep Slack-specific provider payload mapping inside `connectors/slack`. Shared
contracts such as `OAuthInstallation`, `SourceConnection`, `RawEvent`,
`WebhookDelivery`, `BackfillJob`, and `ProviderCursor` stay provider-neutral.

## Data Model

Add or complete records and migrations for:

- `oauth_installations`,
- `secret_refs` or local secret-store metadata if not already present,
- `source_connections`,
- `webhook_deliveries`,
- `backfill_jobs`,
- `provider_cursors`.

Use existing `raw_events` for Slack payloads.

Lifecycle states:

```txt
OAuthInstallation: installing -> active -> needs_reauth -> disabled -> revoked
SourceConnection: active -> paused -> disabled
BackfillJob: queued -> running -> completed
                       -> retrying -> failed -> deadlettered
WebhookDelivery: received -> verified -> persisted
                         -> ignored_duplicate -> failed -> deadlettered
ProviderCursor: active -> stale -> failed -> reset_requested
```

Cursor advancement rule: do not advance a cursor past an event until the
corresponding raw event is durably persisted or intentionally recorded as a
duplicate no-op.

## OAuth And Secrets

Slack OAuth should:

- generate and validate `state`,
- exchange authorization codes server-side,
- store token material only behind `SecretRef`,
- store token metadata, scopes, team ID, enterprise ID when present, bot/user
  IDs when needed, install timestamps, expiry/revocation state, and health,
- reject missing required scopes at install completion,
- support reauthorization without changing source connection identity.

Required v1 scopes should be explicit in code and tests. Scope drift should mark
the installation unhealthy rather than silently dropping data.

Never log token material, authorization codes, OAuth state values, request
signing secrets, private channel names, message text, file names, file URLs, or
raw payload snippets.

## Source Selection

Workspace/team/channel selection should create `SourceConnection` records for
selected Slack channels.

Selection rules:

- only selected channels are backfilled and accepted for retrieval,
- webhook events for unselected channels are acknowledged but ignored or safely
  recorded as excluded metadata without content,
- channel IDs are stable identifiers; names are metadata and can change,
- source connection changes should trigger fresh backfill or cursor reset as
  appropriate.

For v1, source allowlist selection is channel-level. User-level Slack ACLs are
deferred to the later permissions phase.

## Backfill

Backfill selected channels using Slack Web API history and thread reply calls.

Backfill should:

- create a `BackfillJob` per source connection or channel batch,
- process messages in deterministic order,
- fetch thread replies for threaded messages,
- capture edits, deletes, files, links, reactions if present in message shape,
- persist one raw event per provider-shaped message/reply/file/delete/edit
  unit,
- use idempotency keys based on workspace/team/channel/message timestamp/event
  subtype,
- handle Slack pagination and rate limits,
- checkpoint through `ProviderCursor`,
- retry transient failures with bounded attempts,
- deadletter permanent failures with enough pointer metadata to repair safely.

Large Slack payloads and file bytes should use existing object storage/payload
reference rules instead of Kafka payloads.

## Webhooks

Slack Events API intake should:

- verify request signature and timestamp before reading payload content into
  application logs or pipeline events,
- handle URL verification challenge,
- dedupe retries by Slack event ID and webhook delivery metadata,
- acknowledge quickly after durable receipt,
- persist raw events for message created, changed, deleted, file shared, link
  shared, and thread reply events,
- ignore or safely record unsupported event types,
- never push raw message text into event-envelope payloads.

Webhook processing must be replayable through raw events. A failed downstream
normalization step should not require Slack to resend the webhook.

## Thread Reconstruction

Thread reconstruction belongs at the normalization boundary, but Phase 8 must
provide enough Slack raw events to support it:

- root message and reply timestamps,
- channel and team IDs,
- edit/delete tombstone details,
- user/bot metadata references,
- file/link references,
- permalink metadata when available.

Partition keys should preserve ordering per Slack thread:

```txt
slack:{team_id}:{channel_id}:{thread_ts || message_ts}
```

## File And Link Metadata

For files and diagrams:

- capture file metadata, permalink, MIME type, size, channel/thread/message
  references, and object-storage pointer when downloaded,
- attempt download only for selected channels and allowed file types/sizes,
- route downloaded image/PDF content into the existing `source_files` and OCR
  path,
- record failures such as expired file URLs or missing scopes without blocking
  message ingestion.

For links:

- preserve Slack link metadata and unfurl references when present,
- do not crawl arbitrary external URLs in Phase 8 unless the URL is already part
  of an allowed source path.

## Events

Phase 8 should publish the existing `raw_event.persisted` event after Slack raw
events are stored.

Envelope rules:

- `subject.type=raw_event`,
- `subject.id` is the raw event ID,
- partition key is the Slack thread key when known,
- payload is pointer-only and content-free,
- metadata includes provider `slack`, operation, event type, and source
  connection ID,
- no message text, file names, private URLs, channel names, tokens, or raw
  payload snippets in event payloads.

## Health And Coverage

Expose enough source coverage for retrieval and operators:

- selected channel count,
- last backfill time,
- cursor high/low watermark,
- newest processed Slack timestamp,
- ingestion lag by selected channel,
- webhook verification failures,
- retry/deadletter counts,
- OAuth health and scope drift,
- skipped unsupported event counts,
- file download/OCR backlog.

Retrieval should be able to say Slack is stale or unavailable without crashing.

## Acceptance Criteria

Phase 8 is complete when:

- Slack OAuth install stores token material through `SecretRef`.
- Selected Slack channels become `SourceConnection` records.
- Backfill persists selected-channel Slack messages/replies/files/links as raw
  events.
- Slack Events API verifies signatures, dedupes retries, and persists supported
  events as raw events.
- Cursors advance only after durable raw-event persistence or duplicate no-op.
- Retry/deadletter paths are visible and replayable.
- Real Slack raw events replay through existing normalization into source
  objects/source files/chunks.
- Slack evidence reaches Phase 5 retrieval and Phase 6 context gate.
- Connector logs/events do not leak tokens, message text, private URLs, file
  names, or raw payload snippets.
