# Phase 5 Engineering Review

## Review Verdict

Status: approved with corrections already folded into the plan.

Scope challenge result: proceed as-is. Phase 5 touches retrieval, ranking,
permissions, MCP, evidence persistence, and evals, but those are one product
boundary: cited context retrieval. Gate decisions remain deferred.

## What Already Exists

| Sub-problem | Existing code/docs | Reuse verdict |
| --- | --- | --- |
| MCP tool names | `src/cortex/mcp/server.py` | Implement `retrieve_context` and `get_related_work` behind existing names. |
| Search indexes | Phase 4 plan | Consume FTS/vector candidates; do not rebuild indexes here. |
| Retrieval config | `config/retrieval-v1.yaml` | Use typed loader for candidates, ranking, token budget. |
| Contracts | `RetrievalRequest`, `EvidencePack` | Add DB records and mapper tests. |
| Source allowlists | ADR-009 | Filter before ranking and evidence building. |
| Golden fixture | Phase 1-4 docs | Use COR-123 as the first retrieval eval. |

## NOT In Scope

- `check_context_gate` status behavior.
- Canonical decision approval behavior.
- LLM reranking or synthesis.
- Real provider ACL snapshots.
- Real provider embedding calls.
- New indexing/chunking behavior.

## Architecture Review

1. [P1] (confidence: 9/10) `plan.md` — permissions must happen before ranking
   and candidate summaries. The plan enforces source allowlist filtering before
   ranking/evidence to prevent leakage through debug fields.

2. [P1] (confidence: 9/10) `plan.md` — evidence packs must not include
   non-allowlisted source names, URLs, snippets, file names, chunk IDs, or debug
   IDs. The plan includes this as a hard rule and test target.

3. [P2] (confidence: 8/10) `config/retrieval-v1.yaml` — Phase 5 needs token
   budget values in config. The plan adds `token_budget` so max-token tests do
   not rely on hidden constants.

4. [P2] (confidence: 8/10) `plan.md` — gate-like output can creep into
   retrieval. The plan explicitly forbids returning `allow`, `warn`, or `block`.

5. [P2] (confidence: 8/10) `plan.md` — hybrid retrieval needs explicit partial
   failure semantics. The plan now says one failed candidate path returns
   `partial_results`, while all candidate paths failing marks the request failed.

## Code Quality Review

1. [P2] (confidence: 8/10) `implementation-checklist.md` — retrieval pipelines
   can become one large service. Keep query planning, candidates, permissions,
   ranking, evidence building, rendering, and publishing as separate modules.

2. [P2] (confidence: 8/10) `implementation-checklist.md` — candidate summaries
   need structured debug data, but debug data is a leak risk. Store only safe
   IDs/counts/scores after allowlist filtering.

3. [P2] (confidence: 8/10) `config/retrieval-v1.yaml` — ranking weights should
   be validated as a coherent set. The plan now requires base ranking weights to
   sum to `1.0`, with additive boosts validated separately.

4. [P3] (confidence: 7/10) DB record-to-DTO mapper tests should cover
   `RetrievalRequest` and `EvidencePack`, especially JSON fields and status enum
   serialization.

## Test Review

Detected framework: Python, pytest, pytest-asyncio.

```txt
CODE PATHS                                            AGENT FLOWS
[+] Retrieval service                                [+] retrieve_context
  ├── [★★  PLANNED] query planner                       ├── [★★  PLANNED] golden COR-123
  ├── [★★  PLANNED] FTS candidates                      ├── [★★  PLANNED] compact text + JSON
  ├── [★★  PLANNED] vector candidates                   └── [★★  PLANNED] no gate status
  ├── [★★  PLANNED] relationship expansion
  ├── [★★  PLANNED] partial candidate failure handling
  ├── [★★★ PLANNED] permission filter
  ├── [★★  PLANNED] rank/merge
  └── [★★  PLANNED] evidence builder

[+] Evidence persistence                              [+] get_related_work
  ├── [★★  PLANNED] retrieval request lifecycle          ├── [★★  PLANNED] issue/PR/thread related output
  ├── [★★  PLANNED] evidence pack lifecycle             └── [★★  PLANNED] citations resolve
  └── [GAP]        record-to-DTO mapper tests

COVERAGE: 19/20 paths planned (95%) | GAPS: 1
QUALITY: ★★★:1 ★★:18 ★:0
```

Missing test to add during implementation:

- mapper tests from `RetrievalRequestRecord` and `EvidencePackRecord` to
  Pydantic DTOs, including JSON fields, statuses, timestamps, and versions.

## Performance Review

1. [P2] (confidence: 8/10) Candidate retrieval must apply limits at each source
   path before merge. The plan uses config limits for FTS, vector, relationship,
   merged candidates, final evidence, and per-source caps.

2. [P2] (confidence: 8/10) Token rendering must not repeatedly rescan full
   chunks. Build snippets once and track estimated tokens.

3. [P3] (confidence: 7/10) Relationship expansion can grow quickly. Keep it
   deterministic and limit-bound in Phase 5.

## Failure Modes

| Codepath | Production failure | Planned handling | Gap |
| --- | --- | --- | --- |
| FTS/vector search | Cross-tenant candidates returned. | Workspace filters and tests. | No gap. |
| Permissions | Exclusion summary leaks source name. | Safe counts/categories only. | No gap. |
| Ranking | Exact issue evidence buried. | Exact ID ranking tests. | No gap. |
| Token budget | Critical evidence dropped silently. | Omission recorded in missing/candidate summary. | No gap. |
| MCP | Tool implies gate status. | Tests assert no allow/warn/block. | No gap. |
| Events | Evidence snippets leak in event payload. | Pointer-only envelope tests. | No gap. |

No critical silent gap found.

## Diagrams To Keep

Add inline ASCII comments where useful:

- `src/cortex/retrieval/service.py`: query -> candidates -> filter -> rank ->
  evidence.
- `src/cortex/retrieval/permissions.py`: allowlist filter/redaction flow.
- `src/cortex/retrieval/evidence.py`: candidate -> claim/citation/token budget
  flow.

## Parallelization Strategy

| Step | Modules touched | Depends on |
| --- | --- | --- |
| Persistence/migrations | `src/cortex/db`, `alembic`, `tests/retrieval` | — |
| Config/query planner | `src/cortex/retrieval`, `tests/retrieval` | config file |
| Candidate retrievers | `src/cortex/retrieval`, `tests/retrieval` | Phase 4 indexes |
| Permission/ranking | `src/cortex/retrieval`, `tests/retrieval` | candidate shape |
| Evidence builder/rendering | `src/cortex/retrieval`, `tests/retrieval` | ranking output |
| MCP tools/events/evals | `src/cortex/mcp`, `src/cortex/retrieval`, `tests/mcp` | service output |

Parallel lanes:

- Lane A: persistence.
- Lane B: config/query planner.
- Lane C: candidate retrievers after query planner interfaces.
- Lane D: permission/ranking after candidate shape.
- Lane E: evidence/rendering after D.
- Lane F: MCP/events/evals last.

Conflict flags: most work touches `src/cortex/retrieval`; define interfaces
first if parallelizing.

## Completion Summary

- Step 0: Scope Challenge — scope accepted as-is.
- Architecture Review: 5 issues reviewed, corrections folded in.
- Code Quality Review: 4 issues reviewed, 1 mapper-test reminder remains.
- Test Review: diagram produced, 1 gap identified.
- Performance Review: 3 issues found.
- NOT in scope: written.
- What already exists: written.
- TODOs: none added.
- Failure modes: 0 critical gaps.
- Outside voice: skipped.
- Parallelization: 6 lanes, 2 early parallel lanes, rest dependency-sequenced.
- Lake Score: 5/5 recommendations choose the complete option.
