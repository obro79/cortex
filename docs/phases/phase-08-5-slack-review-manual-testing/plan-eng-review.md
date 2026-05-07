# Phase 8.5 Engineering Review

## Review Verdict

Status: approved as a required post-Phase-8 gate.

Scope challenge result: keep this phase review-only. It may produce bug-fix
work, but bug fixes should be committed as Phase 8 fixes and then rechecked by
Phase 8.5 evidence. Do not let this phase turn into Phase 9 implementation.

## What Already Exists

| Sub-problem | Existing code/docs | Reuse verdict |
| --- | --- | --- |
| Phase 8 commit strategy | Phase 8 implementation checklist and eng review | Review commit stack directly. |
| Slack connector scope | Phase 8 plan | Use as expected behavior baseline. |
| Automated tests | Phase 8 test plan | Run before manual review. |
| Redaction rules | Phase 8 plan and ADR-012 | Use as blocking security checklist. |
| File/OCR behavior | ADR-011 | Verify metadata/OCR path manually. |
| Retrieval/gate | Phase 5/6 plans | Confirm Slack evidence reaches both. |

## NOT In Scope

- New providers.
- Slack approval bot.
- UI polish beyond review of existing health/evidence/gate outputs.
- Broad refactors.
- Production rollout.

## Architecture Review

1. [P1] (confidence: 9/10) `plan.md` - Phase 8.5 must have blocking power. The
   plan requires explicit approval before Phase 9.

2. [P1] (confidence: 9/10) `plan.md` - redaction audit must include review
   artifacts, not only app logs. Screenshots and run logs can leak real data.

3. [P1] (confidence: 8/10) `plan.md` - data-flow map must name actual code
   paths, records, events, redaction boundaries, and tests. A conceptual diagram
   is not enough.

4. [P2] (confidence: 8/10) `plan.md` - failure drills should include both
   provider-edge failures and downstream replay failures. The plan covers both.

5. [P2] (confidence: 7/10) `plan.md` - live-dev testing can be unavailable.
   Recorded-real mode is a good fallback as long as final report names the gap.

## Code Review Standard

Findings should be reported in code-review style:

- severity,
- file/line,
- risk,
- reproduction or reasoning,
- required fix,
- status.

Default severity:

- P0: confirmed secret/content leak or destructive data loss.
- P1: auth/signature/cursor/idempotency bug that can corrupt or expose data.
- P2: reliability, health, stale coverage, or confusing operator behavior.
- P3: maintainability or documentation issue.

P0/P1 findings block Phase 9. P2 findings can be accepted only with explicit
rationale in the final report.

## Manual Test Review

```txt
CODE PATHS                                      MANUAL FLOWS
[+] OAuth/secret boundary                       [+] install Slack app
  ├── [★★★ REVIEW] token redaction                ├── [★★ REVIEW] select channels
  ├── [★★ REVIEW] scope drift                     ├── [★★ REVIEW] run backfill
  └── [★★ REVIEW] reauth state                    ├── [★★ REVIEW] send webhook events
[+] Backfill/webhooks                             ├── [★★ REVIEW] retrieve Slack evidence
  ├── [★★★ REVIEW] signature verification         └── [★★ REVIEW] gate on Slack evidence
  ├── [★★★ REVIEW] cursor/idempotency
  └── [★★ REVIEW] retry/deadletter
[+] Security/redaction
  └── [★★★ REVIEW] logs/events/API/run logs/screenshots

COVERAGE TARGET: 100% of Phase 8 critical paths manually reviewed.
```

## Performance And Operability Review

Check:

- backfill does not require loading an entire channel into memory,
- webhook route acknowledges after durable receipt,
- rate-limit retry state is visible,
- health queries do not scan raw payloads,
- connector lag is understandable,
- replay procedure is documented enough to use during failure.

## Failure Modes

| Failure | Required Phase 8.5 evidence |
| --- | --- |
| Token leak | Redaction search over logs/API/events/run artifacts. |
| Spoofed webhook | Invalid signature drill. |
| Skipped Slack event | Cursor crash/resume drill. |
| Duplicate message | Backfill/webhook duplicate no-op evidence. |
| Unselected channel leak | Unselected event drill and retrieval check. |
| File download failure | Message ingestion still succeeds. |
| Downstream failure | Raw event replay rebuilds normalized objects. |
| Operator confusion | Health/source coverage visual review finding. |

## Commit Strategy

Review evidence should land in small commits:

1. `phase 8.5: add Slack connector review evidence`
2. `phase 8.5: add Slack manual walkthrough results`
3. `phase 8.5: add Slack redaction and failure drills`
4. `phase 8.5: record Phase 9 readiness decision`

Implementation bug fixes found during review should not be hidden in evidence
commits. Commit them separately as Phase 8 fix commits, then add recheck
evidence.

## Completion Summary

- Scope: review-only gate accepted.
- Architecture Review: 5 issues reviewed, corrections folded in.
- Code Review Standard: severity/blocking rules defined.
- Manual Test Review: critical path matrix defined.
- Performance/Operability Review: connector health and replay included.
- Failure modes: 8 drills/checks required.
- Commit strategy: evidence commits separated from bug-fix commits.
- Approval rule: no Phase 9 until final report says `APPROVED_FOR_PHASE_9`.
