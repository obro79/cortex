# Phase 10 Engineering Review

## Review Verdict

Status: approved with corrections folded into the plan.

Scope challenge result: proceed, but keep it as security hardening. Phase 10
should not become enterprise IAM, full provider ACL parity, a public admin UI,
or a deletion/retention mega-phase. It should make the v1 source allowlist model
real and safe across all sources and outputs.

## What Already Exists

| Sub-problem | Existing code/docs | Reuse verdict |
| --- | --- | --- |
| Source allowlist model | ADR-009, Phase 5/8/9 plans | Centralize and harden. |
| Secret refs | ADR-012 and connector plans | Enforce and test consistently. |
| Webhook security | ADR-013 and connectors | Include in security audit. |
| Retrieval filtering | Phase 5 plan | Recheck every candidate/evidence path. |
| Context gate redaction | Phase 6 plan | Harden hidden-source output. |
| Manual review pattern | Phase 8.5 | Reuse final approve/block report. |
| Event payload rules | pipeline envelope docs | Test pointer-only events. |

## NOT In Scope

- Full enterprise SSO/RBAC.
- Provider-native per-user ACL enforcement.
- Public admin console.
- Full deletion/retention workflow.
- Phase 11 observability dashboards/alerts.
- New connectors.

## Architecture Review

1. [P1] (confidence: 9/10) `plan.md` - source allowlist enforcement must happen
   before ingestion, replay, retrieval, relationship expansion, debug output,
   and source coverage. The plan enumerates all boundaries.

2. [P1] (confidence: 9/10) `plan.md` - non-allowlisted metadata leakage is a
   security bug, not a UX bug. The plan blocks title, URL, external ID, chunk
   ID, source object ID, source name, and file name leaks.

3. [P1] (confidence: 9/10) `plan.md` - allowlist removal must block retrieval
   immediately even if derived cleanup is still running.

4. [P1] (confidence: 8/10) `plan.md` - token material must stay behind
   `SecretRef`; connector health and audit logs should use metadata only.

5. [P2] (confidence: 8/10) `plan.md` - identity mapping must be later-ready and
   should not imply full ACL enforcement in Phase 10.

6. [P2] (confidence: 8/10) `plan.md` - audit logs must be useful but sanitized.
   Do not audit raw private snippets or secrets.

7. [P1] (confidence: 9/10) `plan.md` - audit logging without authorization is
   insufficient. The plan now requires a minimal admin actor check for
   allowlist, connector auth, replay/reindex, debug export, repair, and
   permission snapshot actions.

## Code Quality Review

1. [P2] (confidence: 8/10) Avoid scattering permission checks in provider code.
   Provider modules can supply source metadata; `PermissionService` should make
   allow/deny decisions.

2. [P2] (confidence: 8/10) Redaction helpers should be shared by logs, events,
   API responses, debug output, run-log scans, and tests.

3. [P2] (confidence: 8/10) Permission snapshot and identity mapping models
   should store hashes/protected references where possible.

4. [P3] (confidence: 7/10) Add test helpers that assert absence of hidden
   source identifiers across nested JSON responses.

## Test Review

Detected framework: Python, pytest, pytest-asyncio.

```txt
CODE PATHS                                      SECURITY FLOWS
[+] Permission service                          [+] non-allowlisted retrieval
  ├── [★★★ PLANNED] fail closed                   ├── [★★★ PLANNED] no metadata leak
  ├── [★★★ PLANNED] allowlist removal             ├── [★★★ PLANNED] immediate block
  └── [★★ PLANNED] safe source coverage           └── [★★ PLANNED] cleanup enqueued
[+] Secret boundary
  ├── [★★★ PLANNED] SecretRef only
  └── [★★★ PLANNED] logs/API/events/audit scan
[+] Debug safety
  ├── [★★★ PLANNED] workbench/retrieval inspector
  └── [★★ PLANNED] deadletters/pipeline runs
[+] Audit
  ├── [★★★ PLANNED] minimal admin authorization
  └── [★★ PLANNED] append-only sanitized actions

COVERAGE: 11/11 critical paths planned (100%) | GAPS: 0
QUALITY: ★★★:8 ★★:3 ★:0
```

## Performance Review

1. [P2] (confidence: 8/10) Permission checks must be index-backed and cheap in
   retrieval. Avoid per-candidate DB round trips.

2. [P2] (confidence: 8/10) Allowlist snapshot hashes should be cached per
   request/workspace/source set.

3. [P2] (confidence: 7/10) Redaction scans for run artifacts can be offline and
   should not run on hot request paths.

4. [P3] (confidence: 7/10) Allowlist removal cleanup can be async as long as
   retrieval eligibility blocks synchronously.

## Failure Modes

| Codepath | Production failure | Planned handling | Gap |
| --- | --- | --- | --- |
| Retrieval | Hidden chunk returned. | Multi-stage allowlist filtering and tests. | No gap. |
| Source coverage | Hidden repo/channel name exposed. | Aggregate counts only. | No gap. |
| Allowlist removal | Stale vector remains retrievable. | Immediate eligibility block plus cleanup. | No gap. |
| Replay | Removed source recreated. | Replay checks current scopes/tombstones. | No gap. |
| Secret boundary | Token appears in audit/log. | Secret scans and redaction tests. | No gap. |
| Debug output | Deadletter exposes payload. | Debug safety audit. | No gap. |
| Identity mapping | Treated as real ACL. | Later-ready only, not enforcement. | No gap. |
| Admin action | Non-admin triggers replay/export/allowlist change. | Minimal admin authorization and denied-attempt audit. | No gap. |

Residual risk: source allowlists are still coarser than provider-native
per-user ACLs. The final security report must state this clearly and limit the
approved usage model to selected-source team contexts.

## Parallelization Strategy

| Step | Modules touched | Depends on |
| --- | --- | --- |
| Models | `src/cortex/db`, `permissions`, `security` tests | - |
| Permission service | `permissions/service.py`, provider adapters | models |
| Ingestion/replay enforcement | connectors, raw-event replay | permission service |
| Retrieval/gate hardening | retrieval, context_gate | permission service |
| Secrets/redaction | security, connectors, events/logs | shared helpers |
| Admin auth/audit logging | security/admin_auth, security/audit, admin actions | models |
| Review evidence | run logs | tests/drills |

Parallel lanes:

- Lane A: models and mapper tests.
- Lane B: permission service after models.
- Lane C: secret/redaction helpers after models.
- Lane D: retrieval/gate hardening after permission service.
- Lane E: audit logging after models.

Conflict flags: retrieval permission filtering and debug redaction touch shared
output schemas. Lock redaction response shapes before broad edits.

## Commit Strategy

Use multiple commits:

1. `phase 10: add permission and audit models`
2. `phase 10: add permission service`
3. `phase 10: enforce permissions in ingestion`
4. `phase 10: harden retrieval permission filtering`
5. `phase 10: harden secret boundaries`
6. `phase 10: harden debug redaction`
7. `phase 10: add admin authorization and audit logging`
8. `phase 10: record security review results`

Each commit should include focused tests for its slice. P0/P1 security fixes
should be isolated and followed by recheck evidence.

## Completion Summary

- Scope Challenge: accepted as v1 security hardening, not enterprise IAM.
- Architecture Review: 7 issues reviewed, corrections folded in.
- Code Quality Review: 4 issues reviewed.
- Test Review: 10 critical paths planned, 0 gaps.
- Performance Review: 4 issues found.
- NOT in scope: written.
- Failure modes: source allowlist residual risk noted.
- Parallelization: 5 lanes after models.
- Commit strategy: 8 reviewable commits.
