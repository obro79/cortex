# Phase 8 Engineering Review

## Review Verdict

Status: approved with corrections folded into the plan.

Scope challenge result: proceed with a narrow connector phase. Phase 8 touches
OAuth, source selection, backfill, webhooks, cursors, files, health, and raw
events, but these are one connector boundary. It should not implement Linear,
GitHub, repo docs, Slack bot approvals, or user-level Slack ACL snapshots.

## What Already Exists

| Sub-problem | Existing code/docs | Reuse verdict |
| --- | --- | --- |
| Raw event persistence | Phase 2 plan and current raw-event model | Reuse; Slack must enter here. |
| Slack normalizer shape | Phase 3 fixture Slack normalizers | Reuse; adapt real payload shapes to same normalization inputs. |
| Files/OCR | ADR-011 and Phase 3/4 file/chunk plans | Reuse metadata/OCR path; no deep vision. |
| Retrieval/gate | Phase 5 and Phase 6 plans | Reuse unchanged agent-facing tools. |
| Secrets | ADR-012 | Implement token storage via `SecretRef`. |
| Permissions v1 | source allowlist/channel selection | Enforce selected-channel boundary. |

## NOT In Scope

- Linear, GitHub, or repo-doc real connectors.
- Slack approval bot.
- Polished connector admin UI.
- Provider-native per-user Slack ACL snapshots.
- Enterprise Grid completeness.
- Arbitrary external link crawling.
- Deep vision-model diagram understanding.

## Architecture Review

1. [P1] (confidence: 9/10) `plan.md` - real Slack must feed the existing
   `raw_events` and `raw_event.persisted` path. The plan explicitly rejects a
   Slack-specific retrieval bypass.

2. [P1] (confidence: 9/10) `plan.md` - token material must never be stored in
   connector tables or returned by API routes. The plan uses `SecretRef` and
   redaction tests.

3. [P1] (confidence: 9/10) `plan.md` - webhook signature verification must
   happen before payload processing. The plan makes invalid signatures reject
   before raw-event creation.

4. [P1] (confidence: 8/10) `plan.md` - cursor advancement must be tied to
   durable raw-event persistence. The plan includes this as a hard rule.

5. [P2] (confidence: 8/10) `plan.md` - unselected-channel events need an
   explicit safe behavior. The plan says acknowledge/ignore or record excluded
   metadata without content.

6. [P2] (confidence: 7/10) `plan.md` - Slack files can fail independently from
   message ingestion. The plan handles expired URLs/missing scopes without
   blocking message raw events.

## Code Quality Review

1. [P2] (confidence: 8/10) Keep Slack-specific API mapping in
   `src/cortex/connectors/slack`. Provider-neutral contracts should not grow
   Slack-only fields unless they are genuinely shared.

2. [P2] (confidence: 8/10) Separate OAuth, source selection, backfill, webhook,
   cursor, file, and health modules. The connector service can orchestrate, but
   should not become one large provider file.

3. [P2] (confidence: 8/10) Use typed provider event mappers at the boundary.
   Downstream normalizers should receive stable raw-event pointers, not Slack
   client objects.

4. [P3] (confidence: 7/10) Add a small redaction helper/test harness for
   connector logs/events/responses so future connectors can reuse it.

## Test Review

Detected framework: Python, pytest, pytest-asyncio.

```txt
CODE PATHS                                       AGENT FLOWS
[+] Slack OAuth                                 [+] install connector
  ├── [★★★ PLANNED] SecretRef token boundary      ├── [★★ PLANNED] select channels
  ├── [★★  PLANNED] required scopes               ├── [★★ PLANNED] backfill
  └── [★★  PLANNED] reauth/scope drift            ├── [★★ PLANNED] receive webhook
[+] Backfill/webhooks                             ├── [★★ PLANNED] replay raw event
  ├── [★★★ PLANNED] signature verification        └── [★★ PLANNED] retrieve/gate Slack evidence
  ├── [★★★ PLANNED] cursor persistence
  ├── [★★  PLANNED] retry/deadletter
  └── [★★  PLANNED] duplicate no-op
[+] Security/redaction
  └── [★★★ PLANNED] no secret/content leaks

COVERAGE: 10/10 paths planned (100%) | GAPS: 0
QUALITY: ★★★:4 ★★:6 ★:0
```

## Performance Review

1. [P2] (confidence: 8/10) Backfill must batch and checkpoint. Avoid loading an
   entire channel history into memory.

2. [P2] (confidence: 8/10) Webhook route must acknowledge quickly after durable
   receipt. Heavy normalization/file/OCR work should stay async.

3. [P2] (confidence: 7/10) Rate limits should be handled centrally in the Slack
   client adapter so backfill and file downloads share behavior.

4. [P3] (confidence: 7/10) Health queries should use indexed cursor/job/delivery
   metadata, not raw payload scans.

## Failure Modes

| Codepath | Production failure | Planned handling | Gap |
| --- | --- | --- | --- |
| OAuth | Token revoked or scopes drift. | Mark install unhealthy/needs reauth. | No gap. |
| Webhook | Spoofed request. | Signature and timestamp verification before processing. | No gap. |
| Backfill | Cursor advances then process crashes. | Advance only after persistence or duplicate no-op. | No gap. |
| Backfill/webhook | Duplicate Slack message. | Idempotency keys and duplicate no-op. | No gap. |
| Files | File URL expired or scope missing. | Record failure; do not block message ingestion. | No gap. |
| Permissions | Event from unselected channel. | Acknowledge/ignore without content leakage. | No gap. |
| Retrieval | Slack source stale/unavailable. | Source coverage reports stale/unavailable. | No gap. |

Residual risk: until Phase 10 implements richer permission/security work, Phase
8 relies on selected Slack channels as the source boundary. This is acceptable
for v1 but must be explicit in connector setup and tests.

## Diagrams To Keep

Add inline ASCII comments where useful:

- `src/cortex/connectors/slack/backfill.py`: fetch -> persist -> cursor advance.
- `src/cortex/connectors/slack/webhooks.py`: verify -> delivery -> raw event.
- `src/cortex/connectors/slack/files.py`: metadata -> download -> source file/OCR.

## Parallelization Strategy

| Step | Modules touched | Depends on |
| --- | --- | --- |
| Persistence/migrations | `src/cortex/db`, `alembic`, connector tests | - |
| OAuth/secrets | `src/cortex/connectors/slack/oauth.py`, API tests | persistence |
| Source selection | `sources.py`, source connection tests | OAuth/persistence |
| Backfill/cursors | `backfill.py`, `cursors.py`, raw-event tests | source selection |
| Webhooks | `webhooks.py`, API tests | persistence |
| Files/links | `files.py`, source-file tests | backfill/webhook mapping |
| Health/coverage | `health.py`, retrieval coverage tests | jobs/cursors/deliveries |

Parallel lanes:

- Lane A: persistence and mapper tests.
- Lane B: OAuth after persistence interfaces.
- Lane C: webhooks after persistence interfaces.
- Lane D: backfill/cursors after source selection.
- Lane E: files and health after raw-event mapping stabilizes.

Conflict flags: connector shared types and DB records are common dependencies.
Lock those interfaces before splitting implementation.

## Commit Strategy

Use multiple commits during implementation instead of one end-of-phase commit.
The desired review stack is:

1. `phase 8: add connector persistence models`
2. `phase 8: add Slack OAuth install flow`
3. `phase 8: add Slack source selection`
4. `phase 8: add Slack backfill and cursors`
5. `phase 8: add Slack webhook intake`
6. `phase 8: add Slack file and link metadata`
7. `phase 8: replay Slack events through the pipeline`
8. `phase 8: add Slack connector health`
9. optional `phase 8: document Slack connector setup`

Commit only after the focused tests for that slice pass. For Phase 8, this is
more than convenience: OAuth, webhooks, cursors, file handling, and redaction
each carry different risk and should be reviewable separately before the manual
post-Phase-8 checkpoint.

## Completion Summary

- Step 0: Scope Challenge - scope accepted as a narrow Slack connector phase.
- Architecture Review: 6 issues reviewed, corrections folded in.
- Code Quality Review: 4 issues reviewed.
- Test Review: diagram produced, 0 gaps identified.
- Performance Review: 4 issues found.
- NOT in scope: written.
- What already exists: written.
- TODOs: none added.
- Failure modes: selected-channel permission residual risk noted.
- Outside voice: skipped.
- Parallelization: 7 lanes, with persistence as the first shared dependency.
- Commit strategy: 8-9 reviewable commits instead of one end-of-phase commit.
