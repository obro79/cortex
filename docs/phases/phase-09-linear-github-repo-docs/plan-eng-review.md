# Phase 9 Engineering Review

## Review Verdict

Status: approved with corrections folded into the plan.

Scope challenge result: proceed, but keep the phase modular. Linear, GitHub,
repo docs, and deterministic relationships belong together because Phase 9 is
the first task-aware cross-source context loop. The phase should not expand into
provider-native ACLs, broad code indexing, AI-first linking, or connector UI
polish.

## What Already Exists

| Sub-problem | Existing code/docs | Reuse verdict |
| --- | --- | --- |
| Slack connector pattern | Phase 8 and Phase 8.5 docs/run logs | Reuse connector architecture and review lessons. |
| Raw event spine | Phase 2 | All providers/importers feed this path. |
| Normalizers | Phase 3 fixture normalizers | Extend from fixture shapes to real provider shapes. |
| Chunking/indexing | Phase 4 | Reuse source-aware chunking. |
| Retrieval/evidence | Phase 5 | Add cross-source relationship expansion. |
| Context gate | Phase 6 | Add missing/stale/conflict signals across providers. |
| Deterministic linking | ADR-008 | Implement first; AI candidates later. |
| Source allowlists | ADR-009 | Enforce for repos, teams/projects, docs roots. |

## NOT In Scope

- Provider-native per-user ACL snapshots.
- AI-first relationship inference.
- Full source-code indexing outside docs roots.
- Polished connector admin UI.
- Phase 10 security/permissions expansion.
- Production rollout.

## Architecture Review

1. [P1] (confidence: 9/10) `plan.md` - Phase 9 must be gated on Phase 8.5
   approval. The plan makes `UNBLOCKED_FOR_PHASE_9` a prerequisite, matching
   the Phase 8.5 report token.

2. [P1] (confidence: 9/10) `plan.md` - source allowlists are privacy-critical.
   Non-allowlisted repo/team/project/docs metadata must not leak through
   retrieval, source coverage, health, deadletters, or logs.

3. [P1] (confidence: 8/10) `plan.md` - deterministic relationship links should
   be first-class records with method/confidence/evidence metadata, not hidden
   retrieval heuristics.

4. [P2] (confidence: 8/10) `plan.md` - provider-specific API mapping should
   stay in connector modules. Shared pipeline contracts should remain
   provider-neutral.

5. [P2] (confidence: 8/10) `plan.md` - repo docs import must be docs-root
   limited. Full private-repo code indexing belongs to a later phase.

6. [P2] (confidence: 7/10) `plan.md` - cross-source retrieval can grow
   expensive. Relationship expansion should be bounded by type, depth, and
   candidate limits from retrieval config.

7. [P1] (confidence: 9/10) `plan.md` - Phase 9 must not become real customer
   multi-provider ingestion before Phase 10. The plan now limits Phase 9 runs to
   fixtures, redacted recorded-real data, and internal/dev accounts.

8. [P2] (confidence: 8/10) `plan.md` - docs imports must use the raw-event spine
   instead of a vague direct importer event. The plan now requires
   `raw_event.persisted` for imported/changed/deleted docs.

## Code Quality Review

1. [P2] (confidence: 8/10) Keep Linear, GitHub, repo-docs, and relationships in
   separate modules with separate tests.

2. [P2] (confidence: 8/10) Use provider event mappers that convert real API
   payloads into raw-event inputs without leaking provider clients downstream.

3. [P2] (confidence: 8/10) Relationship parser versions should be explicit so
   relationships can be rebuilt when parser rules change.

4. [P3] (confidence: 7/10) Reuse Phase 8 redaction helpers for all new
   providers instead of writing one-off log assertions.

## Test Review

Detected framework: Python, pytest, pytest-asyncio.

```txt
CODE PATHS                                      AGENT FLOWS
[+] Linear connector                            [+] COR-123 task anchor
  ├── [★★ PLANNED] issues/comments/statuses       ├── [★★ PLANNED] Linear -> Slack
  └── [★★★ PLANNED] allowlist exclusion           ├── [★★ PLANNED] Linear -> GitHub
[+] GitHub connector                              ├── [★★ PLANNED] GitHub -> docs/code paths
  ├── [★★ PLANNED] PRs/reviews/commits            └── [★★★ PLANNED] gate stale/conflict
  └── [★★★ PLANNED] private repo exclusion
[+] Repo docs importer
  ├── [★★ PLANNED] markdown/ADR roots
  └── [★★★ PLANNED] docs-root exclusion
[+] Relationships
  ├── [★★ PLANNED] deterministic parsers
  └── [★★ PLANNED] retrieval expansion

COVERAGE: 12/12 critical paths planned (100%) | GAPS: 0
QUALITY: ★★★:4 ★★:8 ★:0
```

## Performance Review

1. [P2] (confidence: 8/10) Backfills/imports must batch and checkpoint. Do not
   load entire repos/projects into memory.

2. [P2] (confidence: 8/10) Relationship expansion must be bounded by source
   allowlist, relationship type, depth, and candidate count.

3. [P2] (confidence: 7/10) Docs import should hash files and skip unchanged
   content to avoid unnecessary chunk/embed/index churn.

4. [P3] (confidence: 7/10) Provider health queries should use job/cursor/source
   metadata, not raw payload scans.

## Failure Modes

| Codepath | Production failure | Planned handling | Gap |
| --- | --- | --- | --- |
| Prerequisite | Phase 8.5 was blocked. | Do not start Phase 9. | No gap. |
| Linear | Non-allowlisted team/project leaks. | Exclusion/redaction tests. | No gap. |
| GitHub | Private repo metadata leaks. | Repo allowlist and redaction tests. | No gap. |
| Docs | Importer indexes outside docs root. | Docs-root allowlist tests. | No gap. |
| Relationships | False links pollute retrieval. | Deterministic parsers, confidence/method metadata, bounded expansion. | No gap. |
| Retrieval | Cross-source expansion is too broad. | Relationship type/depth/candidate bounds. | No gap. |
| Gate | Missing Linear/GitHub context is ignored. | Missing-provider/source coverage gate tests. | No gap. |
| Data boundary | Customer data ingested before hardening. | Fixture/redacted/internal-only until Phase 10. | No gap. |
| Docs importer | Replay/audit bypass. | Docs publish `raw_event.persisted`. | No gap. |

Residual risk: source allowlists are still coarser than provider-native
per-user ACLs. Phase 9 is acceptable only for fixture, redacted recorded-real,
or internal/dev usage. Phase 10 is required before real customer data.

## Parallelization Strategy

| Step | Modules touched | Depends on |
| --- | --- | --- |
| Shared foundations | `src/cortex/connectors`, DB records/tests | Phase 8.5 approval |
| Linear connector | `connectors/linear`, normalization/chunk tests | shared foundations |
| GitHub connector | `connectors/github`, normalization/chunk tests | shared foundations |
| Repo docs importer | `connectors/repo_docs`, docs tests | shared foundations |
| Relationships | `relationships`, parser/repo tests | source objects available |
| Retrieval/gate | `retrieval`, `context_gate` tests | relationships |
| Health/replay | connector health/replay tests | provider lanes |

Parallel lanes:

- Lane A: Linear connector.
- Lane B: GitHub connector.
- Lane C: repo docs importer.
- Lane D: deterministic relationships after initial provider object contracts.
- Lane E: retrieval/gate integration after relationship outputs stabilize.

Conflict flags: shared connector abstractions and source-object enums are common
dependencies. Lock those before splitting provider implementation.

## Commit Strategy

Use multiple commits:

1. `phase 9: extend connector foundations`
2. `phase 9: add Linear connector`
3. `phase 9: add GitHub connector`
4. `phase 9: add repo docs importer`
5. `phase 9: add deterministic relationships`
6. `phase 9: integrate cross-source retrieval`
7. `phase 9: add provider health and replay`
8. `phase 9: complete connector docs and tests`

Each commit should include focused tests for its slice and keep unrelated
provider work out of the diff.

## Completion Summary

- Scope Challenge: accepted as modular cross-source context phase.
- Architecture Review: 8 issues reviewed, corrections folded in.
- Code Quality Review: 4 issues reviewed.
- Test Review: 12 critical paths planned, 0 gaps.
- Performance Review: 4 issues found.
- NOT in scope: written.
- Failure modes: source allowlist residual risk noted.
- Parallelization: 5 lanes after shared foundations.
- Commit strategy: 8 reviewable commits instead of one end-of-phase commit.
