# Phase 8.5 Plan: Slack Connector Review And Manual Testing

## Goal

Run a formal review gate after Phase 8 and before Phase 9. This phase does not
add product features. It verifies that the first real-data connector is safe,
operable, understandable, and genuinely wired into the Cortex retrieval/gate
loop.

```txt
Phase 8 implementation
  -> commit-by-commit code review
  -> data-flow map
  -> manual Slack install/backfill/webhook run
  -> visual/product confirmation
  -> security/redaction audit
  -> replay/failure-mode drills
  -> review report
  -> approve Phase 9 or block with fixes
```

The invariant: no Phase 9 provider work starts until Phase 8.5 produces an
explicit approve/block decision.

## Inputs

- [`../implementation-roadmap.md`](../implementation-roadmap.md#phase-85-slack-connector-review-and-manual-testing)
- [`../phase-08-real-slack-connector/plan.md`](../phase-08-real-slack-connector/plan.md)
- [`../phase-08-real-slack-connector/implementation-checklist.md`](../phase-08-real-slack-connector/implementation-checklist.md)
- [`../phase-08-real-slack-connector/test-plan.md`](../phase-08-real-slack-connector/test-plan.md)
- [`../phase-08-real-slack-connector/plan-eng-review.md`](../phase-08-real-slack-connector/plan-eng-review.md)
- [`../../architecture/handbook.md`](../../architecture/handbook.md)
- [`../../architecture/adrs/011-slack-files-diagrams-ocr/README.md`](../../architecture/adrs/011-slack-files-diagrams-ocr/README.md)
- [`../../architecture/adrs/012-secrets-token-management/README.md`](../../architecture/adrs/012-secrets-token-management/README.md)

## Non-Goals

- No new Linear, GitHub, or repo-docs implementation.
- No new Slack connector feature work unless required to fix a blocking bug.
- No broad refactor unrelated to Phase 8 safety or correctness.
- No production customer rollout decision beyond readiness for Phase 9 planning.
- No replacing automated tests; this phase complements them with manual review
  and operational evidence.

## Review Scope

Review all Phase 8 commits and any supporting code they touched:

- connector persistence and migrations,
- OAuth and secret handling,
- source selection/channel allowlist,
- backfill and provider cursors,
- webhook verification/dedupe/intake,
- Slack file/link metadata handling,
- raw-event replay and normalization,
- connector health/source coverage,
- retrieval/evidence/context-gate integration,
- tests, fixtures, redaction helpers, and setup docs.

## Data-Flow Map

Produce a durable map in `run-logs/` showing:

```txt
OAuth install
  -> OAuthInstallation + SecretRef
  -> SourceConnection(selected channels)
  -> BackfillJob / WebhookDelivery
  -> ProviderCursor
  -> RawEvent + payload ref
  -> raw_event.persisted
  -> SourceObject / SourceFile
  -> SourceChunk / indexes
  -> EvidencePack
  -> ContextGateResult
  -> CanonicalDecision proposal/approval path
```

For each edge, record:

- code module/function,
- DB table or event involved,
- idempotency key,
- redaction boundary,
- failure behavior,
- focused tests covering it.

## Manual Testing Modes

Use two modes:

1. Recorded-real mode: Slack-shaped payloads captured from a dev workspace with
   all secrets and content redacted.
2. Live-dev mode: a real dev Slack workspace/app, selected test channels only,
   and no production/customer data.

Live-dev mode is preferred for final approval if credentials and environment are
available. Recorded-real mode is acceptable for repeatable CI/local evidence.

## Manual Walkthrough

Run and record:

1. Start app/workers with Slack connector config.
2. Complete Slack OAuth install.
3. Select one allowed test channel and one intentionally unselected channel.
4. Trigger backfill.
5. Confirm messages, thread replies, files, and links become raw events.
6. Confirm replay creates Slack source objects/source files/chunks.
7. Send Slack message/edit/delete/thread reply/file/link webhook events.
8. Confirm webhook delivery records, dedupe behavior, and raw events.
9. Run retrieval query that should cite Slack evidence.
10. Run context gate query that should use Slack evidence.
11. Inspect connector health/source coverage/lag.
12. Review logs/events/API responses for redaction.

Capture command outputs, screenshots where useful, and notes under
`docs/phases/phase-08-5-slack-review-manual-testing/run-logs/`.

## Code Review Checklist

Review for:

- Phase 8 commit stack is coherent and reviewable.
- Slack connector does not bypass raw-event persistence.
- Token material is behind `SecretRef`.
- OAuth state/signing secret/token/code values are not logged.
- Webhook verification happens before payload processing.
- Cursor advancement cannot skip unpersisted events.
- Backfill and webhooks dedupe the same Slack event shapes.
- Unselected channels cannot leak content or private metadata.
- File download failures do not block message ingestion.
- Event envelopes are pointer-only and content-free.
- Retrieval/gate behavior uses existing tools and source coverage.
- Tests are focused, meaningful, and not only snapshot assertions.

## Security And Redaction Audit

Search logs, traces, API responses, event payloads, deadletters, run logs,
health output, and screenshots for:

- Slack access token,
- refresh token,
- signing secret,
- OAuth authorization code,
- OAuth state,
- private channel name,
- message text,
- file name,
- private file URL,
- raw Slack payload snippet,
- unselected-channel content,
- hidden source object/chunk IDs in agent-facing output.

Any hit outside the explicit raw payload/object-storage boundary blocks Phase 9.

## Failure-Mode Drills

Run or simulate:

- invalid Slack signature,
- stale Slack timestamp,
- duplicate webhook retry,
- process crash before cursor advancement,
- process crash after raw-event persistence before cursor advancement,
- Slack rate limit during backfill,
- file download expired/missing scope,
- revoked token or missing scope,
- unselected-channel event,
- downstream normalization failure followed by replay.

Each drill should record expected behavior, observed behavior, and fix/block
status.

## Review Report

Create a final report in `run-logs/` with:

- review date,
- branch/commit range reviewed,
- commands run,
- manual walkthrough evidence,
- screenshots/visual evidence references,
- data-flow map link,
- bugs found,
- fixes made or required,
- redaction audit result,
- residual risks,
- final decision: `APPROVED_FOR_PHASE_9` or `BLOCKED`.

## Acceptance Criteria

Phase 8.5 is complete when:

- all Phase 8 commits have been reviewed,
- data-flow map matches actual code paths,
- manual Slack walkthrough has recorded evidence,
- retrieval and context gate are visually/manually confirmed with Slack evidence,
- redaction audit passes,
- failure-mode drills pass or have blocking fixes documented,
- final review report approves Phase 9 or blocks with concrete remediation.
