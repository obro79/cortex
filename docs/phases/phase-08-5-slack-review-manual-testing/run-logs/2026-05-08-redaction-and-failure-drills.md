# Phase 8.5 Redaction And Failure Drills

Date: 2026-05-08

## Redaction Audit

Artifacts reviewed:

- API responses from OAuth, source selection, backfill, health, and webhook
  verification.
- ngrok request list summarized manually without committing raw request bodies.
- Connector logs visible from local `uvicorn`.
- Automated test assertions for pointer-only pipeline payloads.
- Run-log files in this directory.

Search terms used conceptually and in diff review:

- Slack token prefixes and token material
- Slack signing secret
- Slack client secret
- OAuth authorization code
- OAuth state
- Slack raw payload body
- private file URLs
- file names from test fixtures
- selected/unselected channel message text

Result: PASS for committed artifacts and API responses reviewed. Raw Slack
payloads are present only inside the raw payload boundary/ngrok inspector during
manual testing and are not copied into committed run logs.

## Failure Drills

| Drill | Evidence | Observed behavior | Status |
| --- | --- | --- | --- |
| Invalid signature | `tests/connectors/slack/test_webhook_service.py::test_bad_signature_rejected_before_processing` | rejected before raw event publish | PASS |
| Stale timestamp | `SlackWebhookVerifier.verify` tolerance plus API webhook tests | rejected by same verifier path before payload processing | PASS |
| Duplicate webhook retry | `test_webhook_duplicate_retry_noops` | second delivery marked duplicate, no second raw event | PASS |
| Unselected channel event | `test_unselected_channel_is_ignored_without_raw_event` | returns `ignored_unselected`, no event published | PASS |
| Rate limit during backfill | `tests/connectors/slack/test_provider_cursor.py::test_rate_limit_marks_backfill_retrying_without_cursor_advance` | job marked retrying, cursor not advanced | PASS |
| Permanent provider failure | `test_permanent_failure_deadletters_backfill_job` | job deadlettered without cursor advance | PASS |
| Backfill resume duplicate handling | `test_backfill_resume_counts_duplicates_without_rewriting_payloads` | second run creates no additional raw events | PASS |
| File/link metadata redaction | `tests/connectors/slack/test_file_ingestion.py` | file name/private URL excluded; hash retained | PASS |
| Revoked token/scope drift | OAuth missing-scope path plus health status fix in this phase | missing scopes mark `needs_reauth`; health now reports non-active status | PASS |
| Downstream normalization failure followed by replay | normalization worker tests and `RawEventReplayService` tests | raw events can be replayed; malformed normalization can deadletter | PARTIAL |
| Live Slack raw event to source object/chunk/retrieval | manual review of registry and live run | no dedicated live Slack normalizer/chunker/index path yet | BLOCKED |

## Findings

### P1: Live Slack Raw Events Do Not Reach Retrieval/Gate

`src/cortex/normalization/registry.py` currently maps provider `"slack"` to the
fixture normalizer. Live Slack payloads can be persisted and replayed, but they
do not have a production Slack normalizer that emits Slack source objects/files,
chunks, indexes, evidence packs, or context-gate evidence.

Impact: Phase 8.5 cannot honestly approve Phase 9 because the acceptance
criterion "real Slack data reaches retrieval/gate" is not met.

Status: BLOCKING follow-up required.

### P2: Connector Health Previously Reported OAuth As Active Unconditionally

`SlackHealthService.workspace_health` reported `oauth_status: active` regardless
of actual installation records.

Impact: operator health could hide missing-scope/reauth states.

Status: fixed in this phase by deriving status from workspace installations and
adding focused test coverage.
