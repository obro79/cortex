# Phase 6 Autoplan Review

## Review Scope

Plan reviewed:

- [`plan.md`](plan.md)
- [`implementation-checklist.md`](implementation-checklist.md)
- [`test-plan.md`](test-plan.md)
- Phase 6 roadmap,
- context gate schema,
- product plan gate categories,
- ADR-005 gate config,
- Phase 5 evidence-pack plan.

Autoplan mode:

- CEO review: product risk and phase boundary.
- Design review: skipped because Phase 6 has no UI.
- Engineering review: decision rules, permissions, citations, MCP, tests.
- DX review: deterministic eval workflow.

## Executive Verdict

Phase 6 is approved if it stays deterministic, cited, and narrow. This phase
should make clear allow/warn/block decisions over evidence packs, not implement
approval persistence or canonical memory.

## CEO Review

Score: 9/10.

| Premise | Verdict | Reasoning |
| --- | --- | --- |
| Cortex should block high-impact unsafe context. | Accepted | This is the product's sharp edge. |
| Blocking must be narrow and cited. | Accepted | Broad uncited blocks would destroy trust. |
| Human resolution should wait until Phase 7. | Accepted | Phase 6 produces the gate result; Phase 7 records decisions. |
| Permission ambiguity should fail closed. | Accepted | Privacy safety outranks recall. |

## Engineering Review

Score: 8/10.

```txt
evidence_pack
  -> risk classifier
  -> signal extractor
  -> decision engine
  -> context_gate_result
  -> compact cited message
```

Key decisions:

1. Deterministic rules first.
   Decision: no LLM classifier in Phase 6.
2. Every warn/block must cite evidence.
   Decision: uncited high-impact signals fail/warn but do not block silently.
3. Permission ambiguity fails closed.
   Decision: use config and source allowlist safety.
4. Blocks include required actions but do not persist human action.
   Decision: Phase 7 owns approval records.

## DX Review

Score: 8/10.

The local loop should be:

```txt
pytest tests/context_gate tests/mcp/test_check_context_gate.py
```

The plan is useful if COR-123 deterministically blocks with compact cited output
and clear required human actions.

## Risks

| Risk | Mitigation |
| --- | --- |
| Gate blocks without citations. | Citation-required signal tests. |
| Gate leaks hidden source IDs. | Safe renderer and event payload tests. |
| Gate overblocks weak ambiguity. | Threshold/config tests and low-risk warn fixtures. |
| Approval workflow sneaks into Phase 6. | Phase 7 boundary in non-goals. |
| Permission ambiguity returns allow. | Fail-closed priority rule. |

## Final Approval Gate

Approved to implement if:

- warn/block results cite evidence,
- permission ambiguity blocks when configured,
- COR-123 blocks,
- clear evidence allows,
- low-risk ambiguity warns,
- human resolution persistence remains Phase 7.
