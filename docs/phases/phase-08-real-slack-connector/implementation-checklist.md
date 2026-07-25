# Phase 8 Implementation Checklist

## 1. Provider-Neutral Persistence

- Add or complete `OAuthInstallation`, `SecretRef`, `SourceConnection`,
  `WebhookDelivery`, `BackfillJob`, and `ProviderCursor` records.
- Add migrations and indexes from the architecture docs.
- Keep Slack-specific provider metadata in JSON fields only where the
  provider-neutral model needs extension.

Acceptance:

- migrations apply cleanly,
- provider-neutral DTO/record mapper tests pass,
- token material is never stored in ordinary connector tables.

Commit:

- `phase 8: add connector persistence models`

## 2. Slack OAuth

- Implement install-start endpoint/service.
- Implement install-complete endpoint/service.
- Validate OAuth state.
- Exchange authorization code.
- Store token material behind `SecretRef`.
- Store scopes, team ID, enterprise ID, bot/user metadata, and health status.
- Detect missing required scopes and scope drift.

Acceptance:

- successful install creates active `OAuthInstallation`,
- missing scopes fail or mark install unhealthy,
- token/code/state values are redacted from logs and API responses.

Commit:

- `phase 8: add Slack OAuth install flow`

## 3. Source Selection

- List Slack channels available to the installation.
- Create/update selected-channel `SourceConnection` records.
- Track channel IDs as stable source identifiers.
- Handle pause/disable states.
- Trigger backfill or cursor reset when source selection changes.

Acceptance:

- selected channels are the only channels ingested,
- unselected-channel events do not leak content,
- channel rename does not break source identity.

Commit:

- `phase 8: add Slack source selection`

## 4. Backfill

- Implement selected-channel history fetch.
- Implement thread reply fetch.
- Create `BackfillJob` records.
- Persist one raw event per message/reply/file/link/edit/delete unit.
- Use Slack-specific idempotency keys.
- Persist payloads through the raw-event storage path.
- Advance `ProviderCursor` only after persistence or duplicate no-op.
- Handle pagination, rate limits, retries, and deadletters.

Acceptance:

- backfill can stop and resume without duplicating source objects,
- cursor resume test passes,
- rate-limit retry test passes,
- failed permanent events are deadlettered with repair pointers.

Commit:

- `phase 8: add Slack backfill and cursors`

## 5. Webhooks

- Implement Slack Events API route.
- Verify Slack request signature and timestamp.
- Handle URL verification challenge.
- Create `WebhookDelivery` records.
- Dedupe Slack retries by provider event ID/delivery metadata.
- Persist supported events as raw events.
- Acknowledge unsupported events safely.

Acceptance:

- invalid signature rejects before processing,
- duplicate webhook retries no-op,
- message/edit/delete/file/link/thread events persist as raw events,
- webhook event payloads remain content-free after raw storage.

Commit:

- `phase 8: add Slack webhook intake`

## 6. Files And Links

- Capture Slack file metadata and references.
- Download allowed files only from selected channels.
- Store file bytes through object storage.
- Route file metadata and OCR candidates to existing source-file path.
- Preserve link metadata without crawling arbitrary external URLs.

Acceptance:

- file metadata becomes source-file input,
- expired or unauthorized file downloads do not block message ingestion,
- file names/private URLs are not leaked through logs/events.

Commit:

- `phase 8: add Slack file and link metadata`

## 7. Raw-Event Pipeline Integration

- Publish `raw_event.persisted` for Slack raw events.
- Use thread-level partition keys.
- Replay Slack raw events through existing normalizers.
- Preserve edit/delete semantics needed by source object lifecycle.

Acceptance:

- replay creates expected Slack source objects and source files,
- duplicate replay is idempotent,
- edit/delete fixtures update lifecycle correctly.

Commit:

- `phase 8: replay Slack events through the pipeline`

## 8. Health And Coverage

- Expose connector health for OAuth, scopes, source selection, cursors, and
  deadletters.
- Record ingestion lag by channel/source connection.
- Report source coverage to retrieval/evidence pack generation.

Acceptance:

- stale Slack source is visible as stale coverage,
- failed connector does not crash retrieval,
- operator-facing health excludes message/file content.

Commit:

- `phase 8: add Slack connector health`

## 9. MCP/API Surface

- Add minimal connector API routes needed for OAuth, source selection, backfill,
  and health.
- Keep agent-facing retrieval/gate tools unchanged.

Acceptance:

- real Slack data reaches existing `retrieve_context` and
  `check_context_gate`,
- no new agent tool bypasses source allowlists or raw-event replay.

Commit:

- fold into the relevant OAuth/source/backfill/health commits when the API route
  is part of that slice.

## 10. Tests And Docs

- Add tests listed in [`test-plan.md`](test-plan.md).
- Add local setup docs for Slack app configuration and signing secret handling.
- Keep examples redacted.

Acceptance:

- `ruff check .` passes.
- `ruff format --check .` passes.
- `mypy src` passes.
- focused connector tests pass.
- existing retrieval/gate golden tests still pass.

Commit:

- commit remaining docs/manual setup notes as
  `phase 8: document Slack connector setup` if they are not already included in
  the implementation commits.

## Commit Cadence

Do not save Phase 8 for one final commit. Phase 8 is security- and
reliability-sensitive, so commits should be small enough to review independently
and large enough to leave a coherent testable slice.

Recommended order:

1. Provider-neutral persistence and mapper tests.
2. Slack OAuth and secret boundary.
3. Source selection/channel allowlist.
4. Backfill and provider cursors.
5. Webhook verification/dedupe/intake.
6. File/link metadata handling.
7. Raw-event replay through normalization/retrieval/gate.
8. Health/coverage and setup docs.

Each commit should include the tests for its slice. Run a focused connector test
loop before every commit, then run the broader retrieval/gate smoke loop before
the final Phase 8 manual review checkpoint.

## Completion Criteria

Phase 8 is complete when selected real Slack channels can be installed,
backfilled, updated by webhooks, replayed from raw events, normalized into the
same source objects/files as fixtures, and retrieved/gated without leaking
Slack secrets or content through logs/events.
