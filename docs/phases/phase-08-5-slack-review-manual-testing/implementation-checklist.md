# Phase 8.5 Implementation Checklist

## 1. Prepare Review Evidence

- Identify Phase 8 commit range.
- Confirm all Phase 8 commits are pushed or locally available for review.
- Create `run-logs/` for Phase 8.5 evidence.
- Record environment, config mode, and redacted Slack workspace/app setup.

Acceptance:

- reviewer can reproduce the reviewed commit range,
- no secrets appear in setup notes.

## 2. Commit-By-Commit Code Review

- Review persistence/migrations.
- Review OAuth and secret boundary.
- Review source selection/channel allowlist.
- Review backfill/cursor logic.
- Review webhook verification/dedupe.
- Review file/link metadata handling.
- Review raw-event replay integration.
- Review health/source coverage.
- Review tests and setup docs.

Acceptance:

- findings are recorded with file/line references,
- blocking findings are fixed before approval or explicitly marked blocking.

## 3. Data-Flow Map

- Map Slack install to `OAuthInstallation` and `SecretRef`.
- Map selected channel to `SourceConnection`.
- Map backfill/webhook to `RawEvent`.
- Map raw event to source object/file/chunk.
- Map Slack evidence to retrieval and context gate.
- Annotate redaction, idempotency, and failure behavior at each edge.

Acceptance:

- map matches current code,
- every edge names code path, record/event, test coverage, and failure behavior.

## 4. Manual Slack Walkthrough

- Run Slack OAuth install.
- Select allowed and unselected test channels.
- Run backfill.
- Trigger message, edit, delete, thread reply, file, and link paths.
- Run retrieval query with Slack citation.
- Run context gate query using Slack evidence.
- Inspect health/source coverage.

Acceptance:

- walkthrough notes include commands, timestamps, screenshots or terminal
  evidence, and observed record IDs where safe,
- unselected channel content does not appear in outputs.

## 5. Visual/Product Confirmation

- Confirm connector health is understandable.
- Confirm source coverage shows freshness/lag.
- Confirm evidence pack citations point to Slack source objects.
- Confirm context gate message is compact, cited, and actionable.
- Confirm manual reviewer can explain where Slack data is in the pipeline.

Acceptance:

- visual evidence or terminal evidence is attached,
- confusing or misleading output is filed as a finding.

## 6. Security And Redaction Audit

- Search logs.
- Search traces if available.
- Search API responses.
- Search event payloads.
- Search deadletters.
- Search health/source coverage output.
- Search run logs/screenshots before sharing.

Acceptance:

- no Slack secret or content leaks outside explicit raw payload/object-storage
  boundaries,
- any leak blocks Phase 9 until fixed and rechecked.

## 7. Failure-Mode Drills

- Invalid signature.
- Stale timestamp.
- Duplicate webhook retry.
- Cursor crash/resume cases.
- Rate limit/retry.
- Deadletter.
- Revoked token/scope drift.
- File download failure.
- Unselected-channel event.
- Replay after downstream failure.

Acceptance:

- each drill has expected/observed/final status,
- blocking gaps are fixed or Phase 9 remains blocked.

## 8. Review Report

- Summarize review scope.
- Link data-flow map and run logs.
- List bugs found and fixes required.
- List commands/manual checks run.
- Record redaction audit status.
- Record residual risks.
- Decide `APPROVED_FOR_PHASE_9` or `BLOCKED`.

Acceptance:

- final report exists in `run-logs/`,
- decision is explicit and justified.

## Commit Cadence

Phase 8.5 should be committed as evidence accumulates:

1. `phase 8.5: add Slack connector review evidence`
2. `phase 8.5: add Slack manual walkthrough results`
3. `phase 8.5: add Slack redaction and failure drills`
4. `phase 8.5: record Phase 9 readiness decision`

If Phase 8.5 finds implementation bugs, fix those in separate Phase 8 fix
commits, then add Phase 8.5 recheck evidence in a follow-up review commit.
