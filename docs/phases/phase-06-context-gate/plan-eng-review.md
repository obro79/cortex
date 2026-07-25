# Phase 6 Engineering Review

## Review Verdict

Status: approved with corrections folded into the plan.

Scope challenge result: proceed as-is. Context gate touches config, persistence,
signals, risk classification, MCP, rendering, and evals, but these are one
allow/warn/block decision boundary. Approval persistence remains deferred.

## What Already Exists

| Sub-problem | Existing code/docs | Reuse verdict |
| --- | --- | --- |
| Gate contract | `ContextGateResult`, `ContextGateStatus` | Reuse; add DB record and mapper tests. |
| Evidence packs | Phase 5 plan | Consume durable evidence pack fields. |
| MCP tool name | `src/cortex/mcp/server.py` | Implement existing `check_context_gate`. |
| Gate config | `config/retrieval-v1.yaml` | Use typed loader and record `gate_version`. |
| Gate categories | product plan and handbook | Encode deterministic v1 categories. |

## NOT In Scope

- Approval records and canonical decisions.
- LLM risk classification.
- Slack approval bot.
- Provider-native ACL snapshots.
- Retrieval/ranking changes.

## Architecture Review

1. [P1] (confidence: 9/10) `plan.md` — blocks without citations are dangerous.
   The plan requires every warn/block signal to cite evidence.

2. [P1] (confidence: 9/10) `plan.md` — permission ambiguity must fail closed.
   The decision priority blocks permission ambiguity when configured.

3. [P2] (confidence: 8/10) `plan.md` — required human actions can accidentally
   become Phase 7 persistence. The plan outputs required actions only; Phase 7
   persists human decisions.

4. [P2] (confidence: 8/10) `config/retrieval-v1.yaml` — gate thresholds need a
   versioned config source. The plan adds `context_gate.version=gate-v1`.

## Code Quality Review

1. [P2] (confidence: 8/10) Keep risk classification, signal extraction,
   decision rules, and rendering separate. This keeps deterministic rules
   readable and testable.

2. [P2] (confidence: 8/10) Reasons/actions JSON should store structured IDs and
   citation refs, not prose blobs that are hard to validate.

3. [P3] (confidence: 7/10) Add mapper tests from `ContextGateResultRecord` to
   the Pydantic DTO, including enum serialization and JSON fields.

## Test Review

Detected framework: Python, pytest, pytest-asyncio.

```txt
CODE PATHS                                            AGENT FLOWS
[+] Gate service                                     [+] check_context_gate
  ├── [★★  PLANNED] load/create evidence pack           ├── [★★★ PLANNED] COR-123 block
  ├── [★★  PLANNED] risk classifier                     ├── [★★  PLANNED] low-risk warn
  ├── [★★★ PLANNED] signal citations                    ├── [★★  PLANNED] clear allow
  ├── [★★★ PLANNED] permission fail-closed              └── [★★  PLANNED] compact output
  ├── [★★  PLANNED] decision priority
  ├── [★★  PLANNED] renderer
  └── [GAP]        record-to-DTO mapper tests

COVERAGE: 10/11 paths planned (91%) | GAPS: 1
QUALITY: ★★★:3 ★★:7 ★:0
```

Missing test to add during implementation:

- mapper tests from `ContextGateResultRecord` to `ContextGateResult`, including
  status enum serialization, reasons/actions JSON, timestamps, and gate version.

## Performance Review

1. [P2] (confidence: 7/10) Gate evaluation should be O(evidence pack size), not
   re-run retrieval ranking. The plan consumes evidence pack summaries.

2. [P3] (confidence: 7/10) Message rendering should use bounded citation counts
   and compact text to avoid huge MCP responses.

## Failure Modes

| Codepath | Production failure | Planned handling | Gap |
| --- | --- | --- | --- |
| Evidence pack load | Missing/expired pack. | Create via retrieval or fail structured. | No gap. |
| Permission ambiguity | Ambiguous exclusions affect task. | Block when configured. | No gap. |
| Conflict signal | Conflict lacks citation. | Does not block silently. | No gap. |
| Renderer | Hidden source ID leaks. | Safe renderer tests. | No gap. |
| Event | Required action prose leaks in payload. | Pointer-only metadata tests. | No gap. |

No critical silent gap found.

## Diagrams To Keep

Add inline ASCII comments where useful:

- `src/cortex/context_gate/service.py`: evidence pack -> signals -> decision ->
  result.
- `src/cortex/context_gate/decision.py`: decision priority table.
- `src/cortex/context_gate/render.py`: safe compact output rules.

## Parallelization Strategy

| Step | Modules touched | Depends on |
| --- | --- | --- |
| Persistence/migration | `src/cortex/db`, `alembic`, `tests/context_gate` | — |
| Config/risk/signals | `src/cortex/context_gate`, `tests/context_gate` | config file |
| Decision/rendering | `src/cortex/context_gate`, `tests/context_gate` | signals |
| MCP/service integration | `src/cortex/mcp`, `src/cortex/context_gate`, `tests/mcp` | decision/rendering |
| Events/evals | `src/cortex/context_gate`, `tests/context_gate` | persistence + service |

Parallel lanes:

- Lane A: persistence.
- Lane B: config/risk/signals.
- Lane C: decision/rendering after B.
- Lane D: MCP/events/evals after A + C.

Conflict flags: most logic touches `src/cortex/context_gate`; keep interfaces
clear before splitting work.

## Completion Summary

- Step 0: Scope Challenge — scope accepted as-is.
- Architecture Review: 4 issues reviewed, corrections folded in.
- Code Quality Review: 3 issues reviewed, 1 mapper-test reminder remains.
- Test Review: diagram produced, 1 gap identified.
- Performance Review: 2 issues found.
- NOT in scope: written.
- What already exists: written.
- TODOs: none added.
- Failure modes: 0 critical gaps.
- Outside voice: skipped.
- Parallelization: 4 lanes, 2 early parallel lanes, rest dependency-sequenced.
- Lake Score: 5/5 recommendations choose the complete option.
