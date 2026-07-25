# Phase 9 Autoplan Review

## Review Scope

Plan reviewed:

- [`plan.md`](plan.md)
- [`implementation-checklist.md`](implementation-checklist.md)
- [`test-plan.md`](test-plan.md)
- Phase 9 roadmap,
- Phase 8.5 review gate,
- connector architecture,
- deterministic linking ADR,
- source allowlist ADR,
- retrieval and context-gate plans.

Autoplan mode:

- CEO review: does Phase 9 unlock the core product story?
- Design review: source coverage/evidence/gate clarity, no new polished UI.
- Engineering review: connector reuse, replay, relationships, allowlists.
- DX review: commit stack, test loop, debuggability.

## Executive Verdict

Phase 9 is approved to plan, but implementation is gated on Phase 8.5 approval.
It should be built as three source lanes plus deterministic relationships, not
as one giant provider expansion.

Implementation data boundary: Phase 9 may use fixtures, redacted recorded-real
payloads, and internal/dev accounts only. Real customer data waits for Phase 10
approval.

## CEO Review

Score: 9/10.

| Premise | Verdict | Reasoning |
| --- | --- | --- |
| Phase 9 is the full first wow path. | Accepted | Linear task + GitHub evidence + repo docs + Slack decisions is the product story. |
| It should wait for Phase 8.5. | Accepted | More connectors amplify any Slack-era trust bugs. |
| Deterministic relationships first. | Accepted | Explainability matters more than AI recall at this stage. |
| Source allowlists remain v1. | Accepted with risk | Good enough for early use if exclusion tests are strict. |
| Real customer data can wait until Phase 10. | Accepted | Multi-provider ingestion before security hardening would amplify risk. |

## Design Review

Score: 8/10.

The user-facing output must make source coverage legible:

- what providers were searched,
- which providers were stale/missing,
- which relationships pulled evidence in,
- why the context gate warned or blocked.

No polished connector UI is needed, but health/evidence outputs must be readable
enough for manual review and debugging.

## Engineering Review

Score: 8/10.

```txt
Linear + GitHub + docs
  -> raw events/source objects/chunks
  -> deterministic relationships
  -> retrieval expansion
  -> context gate
```

Key decisions:

1. Reuse Slack connector foundations.
2. Keep Linear, GitHub, and docs importer commits separable.
3. Build deterministic links before AI candidates.
4. Treat source allowlist failures as blocking security bugs.
5. Keep provider-specific mapping out of shared retrieval logic.
6. Keep cross-provider person identity out of Phase 9 relationships.

## DX Review

Score: 8/10.

The local loop should be:

```txt
pytest tests/connectors/linear tests/connectors/github tests/connectors/repo_docs tests/relationships
```

Then run:

```txt
pytest tests/retrieval tests/context_gate
```

Reviewability depends on small commits: Linear, GitHub, docs, relationships,
retrieval/gate, health.

## Risks

| Risk | Mitigation |
| --- | --- |
| Three providers create a giant diff. | Commit lanes separately. |
| Relationship builder over-expands scope. | Deterministic links only in v1. |
| Non-allowlisted repo/team/docs metadata leaks. | Security/redaction tests block. |
| GitHub/Linear APIs differ from Slack patterns. | Reuse shared abstractions but keep provider mapping local. |
| Docs import becomes full code indexing. | Limit to explicit docs roots. |
| Phase 8.5 issues get ignored. | Phase 9 prerequisite gate requires approval. |
| Phase 9 ingests customer data before hardening. | Explicit data boundary until Phase 10 approval. |

## Final Approval Gate

Approved to implement if:

- Phase 8.5 says `UNBLOCKED_FOR_PHASE_9`,
- Phase 9 data is fixture/redacted/internal-only until Phase 10 approval,
- provider work is split into reviewable commits,
- deterministic relationships remain the relationship scope,
- source allowlist redaction tests are included,
- COR-123-style retrieval/gate remains the golden end-to-end validation.
