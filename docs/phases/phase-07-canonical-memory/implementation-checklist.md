# Phase 7 Implementation Checklist

## 1. Persistence

- Add `CanonicalDecisionRecord`.
- Add `ApprovalRecordRecord`.
- Add migrations and indexes from `v1-entity-state-schema.md`.
- Standardize lifecycle on the current `ApprovalStatus` enum values.
- Keep approval records append-only.

Acceptance:

- lifecycle transitions are enforced,
- approval records cannot be mutated through normal repository methods,
- decision text/rationale is not logged.

Commit:

- `phase 7: add canonical memory persistence`

## 2. Proposal Service

- Implement `propose_canonical_decision`.
- Load context gate result and/or evidence pack.
- Validate scope, citations, stale/superseded evidence, and source allowlist
  safety.
- Create `canonical_decision(status=needs_review)`.

Acceptance:

- proposal never creates `approved`,
- missing citations fail validation,
- proposal response includes compact text and structured JSON.

Commit:

- `phase 7: add canonical proposal service`

## 3. Approval Service

- Implement `approve_canonical_decision`.
- Require human `actor_id`.
- Reject agent-only approval attempts.
- Support `approve`, `edit`, `proceed_with_warning`, `mark_unresolved`,
  `reject`, `stop`, and `supersede`.
- Create immutable approval records.

Acceptance:

- approve preserves proposal text,
- edit requires final text and preserves original text,
- proceed-with-warning does not approve canonical memory,
- reject/stop/mark-unresolved do not become retrievable canonical truth.

Commit:

- `phase 7: add human approval workflow`

## 4. Supersession

- Support replacing an approved/edited canonical decision.
- Mark old decision `superseded`.
- Link old/new decision IDs.
- Preserve citations and approval records for both decisions.

Acceptance:

- old decision no longer ranks as active canonical truth,
- superseded evidence remains visible as historical context,
- cycles are rejected.

Commit:

- include in `phase 7: add human approval workflow` if small,
- otherwise commit separately as `phase 7: add canonical supersession`.

## 5. Retrieval Priority Hook

- Add approved/edited canonical decisions to retrieval candidate flow.
- Rank active canonical decisions above stale/conflicting source evidence.
- Exclude rejected, marked unresolved, proceed-with-warning-only, and
  superseded decisions from canonical truth ranking.

Acceptance:

- approved decision appears in future retrieval,
- stale evidence remains visible but lower ranked,
- rejected/unresolved decisions do not appear as canonical truth.

Commit:

- `phase 7: prioritize approved canonical decisions`

## 6. MCP Tools

- Wire `propose_canonical_decision`.
- Wire `approve_canonical_decision`.
- Return structured errors for missing actor, invalid action, invalid transition,
  missing citations, and unknown decision IDs.

Acceptance:

- tool smoke tests pass,
- agent cannot silently approve,
- human approval metadata is returned.

Commit:

- `phase 7: expose canonical memory MCP tools`

## 7. Event Publisher

- Publish `canonical_decision.approved` after approve/edit actions.
- Keep payload pointer-only and content-free.

Acceptance:

- exact envelope tests pass,
- no decision text, rationale, snippets, actor secrets, or hidden source IDs in
  event payloads.

Commit:

- include in `phase 7: expose canonical memory MCP tools` if tiny,
- otherwise commit separately as `phase 7: publish canonical approval events`.

## 8. Tests And Docs

- Add tests listed in [`test-plan.md`](test-plan.md).
- Keep Phase 5/6 golden retrieval/gate tests in focused loop.

Acceptance:

- `ruff check .` passes.
- `ruff format --check .` passes.
- `mypy src` passes.
- `pytest` passes.

Commit:

- commit test/doc-only cleanup separately as `phase 7: complete canonical memory tests`
  only if the prior commits left meaningful follow-up test/doc changes.

## Commit Cadence

Do not save all Phase 7 work for one final commit. Commit each reviewable slice
after its focused tests pass and before moving to the next dependency-heavy
slice.

Recommended order:

1. Persistence and mapper tests.
2. Proposal service.
3. Approval service plus supersession.
4. Retrieval priority hook.
5. MCP tools and pointer-only event publisher.
6. Final focused tests/docs cleanup if needed.

Each commit should leave the repo in a coherent state for that slice. If a slice
requires temporary scaffolding, keep it behind tests or feature wiring that does
not affect existing Phase 5/6 behavior.

## Completion Criteria

Phase 7 is complete when:

- canonical memory cannot become active without human approval,
- approvals are auditable,
- edited/superseded decisions preserve provenance,
- future retrieval prioritizes approved decisions,
- historical stale/conflicting evidence remains visible with citations.
