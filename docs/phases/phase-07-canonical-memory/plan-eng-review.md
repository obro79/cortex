# Phase 7 Engineering Review

## Review Verdict

Status: approved with corrections folded into the plan.

Scope challenge result: proceed as-is. The phase touches proposals, approvals,
canonical decisions, retrieval priority, MCP tools, and audit events, but those
belong to one trust boundary: human-approved canonical memory.

## What Already Exists

| Sub-problem | Existing code/docs | Reuse verdict |
| --- | --- | --- |
| Contracts | `CanonicalDecision`, `ApprovalRecord`, `ApprovalStatus` | Reuse; add DB records and mapper tests. |
| Gate results | Phase 6 plan | Use blocked/warned gate results as proposal input. |
| Evidence packs | Phase 5 plan | Use citations and stale/conflict summaries. |
| MCP names | `src/cortex/mcp/server.py` | Implement existing proposal/approval tool names. |
| Retrieval | Phase 5 plan | Add minimal canonical-priority hook. |

## NOT In Scope

- Slack approval bot.
- Web approval UI.
- LLM-only approval or auto-approval.
- Provider-native identity integration.
- Full deletion/retention workflow.

## Architecture Review

1. [P1] (confidence: 9/10) `plan.md` — human approval is the core trust
   boundary. The plan requires human actor IDs and rejects agent-only approval.

2. [P1] (confidence: 9/10) `plan.md` — proceed-with-warning must not become
   canonical truth. The plan records it as an approval record without approving
   the decision.

3. [P2] (confidence: 8/10) `plan.md` — schema docs mention `active`, while the
   current enum uses `approved`. The plan standardizes on `approved` unless the
   enum is deliberately changed.

4. [P2] (confidence: 8/10) `plan.md` — retrieval prioritization could expand
   into chunk/index work. The plan allows a narrow retrieval hook if full
   canonical chunking is too large.

## Code Quality Review

1. [P2] (confidence: 8/10) Keep proposal and approval services separate.
   Proposal creates review state; approval mutates canonical status with audit.

2. [P2] (confidence: 8/10) Approval records should be append-only at the
   repository API level, not just by convention.

3. [P2] (confidence: 8/10) Supersession needs cycle checks and old/new links.

4. [P3] (confidence: 7/10) Add mapper tests from DB records to `CanonicalDecision`
   and `ApprovalRecord` DTOs, including JSON fields and enum serialization.

## Test Review

Detected framework: Python, pytest, pytest-asyncio.

```txt
CODE PATHS                                            AGENT FLOWS
[+] Canonical memory service                         [+] COR-123 approval loop
  ├── [★★  PLANNED] proposal                           ├── [★★  PLANNED] propose decision
  ├── [★★★ PLANNED] human approval required             ├── [★★★ PLANNED] reject agent approval
  ├── [★★  PLANNED] edit/approve/reject/stop            ├── [★★  PLANNED] approve/edit
  ├── [★★  PLANNED] proceed-with-warning noncanonical   └── [★★  PLANNED] future retrieval priority
  ├── [★★  PLANNED] supersession
  └── [GAP]        record-to-DTO mapper tests

COVERAGE: 9/10 paths planned (90%) | GAPS: 1
QUALITY: ★★★:1 ★★:8 ★:0
```

Missing test to add during implementation:

- mapper tests from `CanonicalDecisionRecord` and `ApprovalRecordRecord` to
  Pydantic DTOs, including status enum serialization, timestamps, citations,
  stale evidence JSON, and approval metadata.

## Performance Review

1. [P2] (confidence: 7/10) Retrieval prioritization should not rescan all
   canonical decisions. Query by workspace/scope/status indexes.

2. [P3] (confidence: 7/10) Supersession chain traversal should be bounded and
   cycle-checked.

## Failure Modes

| Codepath | Production failure | Planned handling | Gap |
| --- | --- | --- | --- |
| Approval | Agent passes fake actor ID. | Require human actor semantics; provider identity integration later. | Residual identity risk until real auth. |
| Proposal | Missing citations. | Validation fails. | No gap. |
| Proceed warning | Treated as canonical truth. | Explicitly non-canonical. | No gap. |
| Supersession | Cycle created. | Reject cycles. | No gap. |
| Event | Decision text leaks in event payload. | Pointer-only payload tests. | No gap. |

Residual risk: until a real auth/identity layer exists, `actor_id` is only as
trustworthy as the caller boundary. The plan should document this as a local/dev
assumption.

## Diagrams To Keep

Add inline ASCII comments where useful:

- `src/cortex/canonical_memory/service.py`: proposal -> approval -> retrieval
  priority.
- `src/cortex/canonical_memory/approvals.py`: action/status transition table.
- repository module: supersession link rules.

## Parallelization Strategy

| Step | Modules touched | Depends on |
| --- | --- | --- |
| Persistence/migration | `src/cortex/db`, `alembic`, `tests/canonical_memory` | — |
| Proposal service | `src/cortex/canonical_memory`, `tests/canonical_memory` | evidence/gate DTOs |
| Approval service | `src/cortex/canonical_memory`, `tests/canonical_memory` | persistence + proposal |
| Retrieval priority | `src/cortex/retrieval`, `src/cortex/canonical_memory` | approved decision records |
| MCP/events | `src/cortex/mcp`, `src/cortex/canonical_memory`, `tests/mcp` | services |

Parallel lanes:

- Lane A: persistence.
- Lane B: proposal service after interfaces.
- Lane C: approval service after A + B.
- Lane D: retrieval priority after A.
- Lane E: MCP/events after C + D.

Conflict flags: canonical memory service files are shared by proposal and
approval; keep those sequential unless interfaces are locked first.

## Commit Strategy

Use multiple commits during implementation instead of one end-of-phase commit.
The desired review stack is:

1. `phase 7: add canonical memory persistence`
2. `phase 7: add canonical proposal service`
3. `phase 7: add human approval workflow`
4. `phase 7: prioritize approved canonical decisions`
5. `phase 7: expose canonical memory MCP tools`
6. optional `phase 7: complete canonical memory tests`

Commit only after the focused tests for that slice pass. This keeps persistence,
trust-boundary logic, retrieval ranking, and MCP wiring independently
reviewable.

## Completion Summary

- Step 0: Scope Challenge — scope accepted as-is.
- Architecture Review: 4 issues reviewed, corrections folded in.
- Code Quality Review: 4 issues reviewed, 1 mapper-test reminder remains.
- Test Review: diagram produced, 1 gap identified.
- Performance Review: 2 issues found.
- NOT in scope: written.
- What already exists: written.
- TODOs: none added.
- Failure modes: residual identity risk noted.
- Outside voice: skipped.
- Parallelization: 5 lanes, 2 early parallel lanes, rest dependency-sequenced.
- Commit strategy: 5-6 reviewable commits instead of one end-of-phase commit.
- Lake Score: 5/5 recommendations choose the complete option.
