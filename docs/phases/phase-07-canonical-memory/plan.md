# Phase 7 Plan: Human-Approved Canonical Memory

## Goal

Let an agent propose a canonical resolution, require a human to approve or edit
it, and make approved decisions durable context for future retrieval.

Phase 7 starts where Phase 6 stops:

```txt
context_gate_result(block/warn)
  -> propose_canonical_decision
  -> canonical_decision(status=needs_review)
  -> human approve/edit/reject/proceed_with_warning/mark_unresolved/stop
  -> approval_record
  -> canonical_decision(status=approved/edited/rejected/marked_unresolved)
  -> canonical_decision.approved
  -> retrieval prioritizes approved decision
```

The invariant: agents can propose, but only a human actor can approve canonical
memory.

## Inputs

- [`../implementation-roadmap.md`](../implementation-roadmap.md#phase-7-human-approved-canonical-memory)
- [`../../architecture/v1-entity-state-schema.md`](../../architecture/v1-entity-state-schema.md#canonical_decisions)
- [`../../architecture/pipeline-event-envelope.md`](../../architecture/pipeline-event-envelope.md)
- [`../phase-06-context-gate/plan.md`](../phase-06-context-gate/plan.md)
- [`../phase-05-retrieval-evidence-packs/plan.md`](../phase-05-retrieval-evidence-packs/plan.md)
- [`../../product-plan.md`](../../product-plan.md)

## Existing Foundation

Earlier phases provide:

- `ContextGateResult` with block/warn required actions,
- `EvidencePack` with citations and stale/conflicting evidence summaries,
- `CanonicalDecision` and `ApprovalRecord` Pydantic contracts,
- MCP tool names `propose_canonical_decision` and
  `approve_canonical_decision`,
- retrieval that can later prioritize approved canonical decisions.

## Non-Goals

- No Slack approval bot.
- No web approval UI.
- No automatic approval by an agent.
- No LLM-only canonical decision creation without explicit human review.
- No full source deletion/retention implementation beyond preserving references
  safely.
- No provider-native identity system beyond actor IDs accepted by MCP/API.

## Architecture

```txt
CanonicalDecisionService
  -> propose_canonical_decision(args)
      -> load context_gate_result/evidence_pack
      -> validate citations and scope
      -> create canonical_decision(status=needs_review)

ApprovalService
  -> approve_canonical_decision(args)
      -> require human actor_id
      -> load proposed canonical_decision
      -> apply action
      -> create immutable approval_record
      -> update canonical_decision status/text/approver/timestamp
      -> supersede older canonical decision when requested
      -> publish canonical_decision.approved when approved/edited
```

Approval records are immutable audit entries. Canonical decisions are durable
customer content and must keep citations but not reproduce deleted source
content after deletion.

## Proposed Module Layout

```txt
src/cortex/canonical_memory/
  __init__.py
  proposals.py
  approvals.py
  retrieval_priority.py
  publishers.py
  render.py
  service.py

tests/canonical_memory/
tests/mcp/test_propose_canonical_decision.py
tests/mcp/test_approve_canonical_decision.py
```

Keep proposal generation deterministic in Phase 7. If a future LLM proposal
helper is added, it must still output `needs_review`, not `approved`.

## Data Model

Add SQLAlchemy records and migrations for:

- `canonical_decisions`,
- `approval_records`.

Fields, indexes, relationships, and lifecycle states should match
`v1-entity-state-schema.md`.

Canonical decision lifecycle:

```txt
proposed -> needs_review -> approved
         -> edited
         -> rejected
         -> marked_unresolved
approved/edited -> superseded
```

The schema doc says `active`; the current code enum uses `approved`. Phase 7
should standardize on `approved` for active canonical decisions unless the enum
is deliberately changed in the same implementation.

Approval records are append-only. Do not update or delete them in normal flows.

## Proposal Flow

`propose_canonical_decision` should:

- require `workspace_id`,
- require `context_gate_result_id` or `evidence_pack_id`,
- derive scope from task hints, issue ID, repo/path, or explicit input,
- produce proposed title and decision text,
- attach source citations from the evidence pack,
- attach stale/superseded evidence references,
- create `canonical_decision(status=needs_review)`,
- return compact proposal text plus structured JSON.

The proposal may be agent-generated, but it is not canonical memory until a
human approves or edits it.

## Approval Flow

`approve_canonical_decision` should:

- require `actor_id` representing a human,
- reject missing or agent-only actor IDs,
- require one action:
  - `approve`,
  - `edit`,
  - `proceed_with_warning`,
  - `mark_unresolved`,
  - `reject`,
  - `stop`,
  - `supersede`,
- create an immutable `approval_record`,
- update the canonical decision state only through allowed transitions,
- preserve original text and final text,
- preserve rationale when provided.

Action behavior:

| Action | Canonical decision effect |
| --- | --- |
| `approve` | status `approved`, final text equals proposal. |
| `edit` | status `edited`, final text required. |
| `proceed_with_warning` | records human override without making a canonical decision approved. |
| `mark_unresolved` | status `marked_unresolved`. |
| `reject` | status `rejected`. |
| `stop` | records stop action; decision remains not approved. |
| `supersede` | marks old approved decision `superseded` and approves replacement. |

Only `approved` and `edited` decisions should be prioritized in future
retrieval.

## Retrieval Integration

Add the minimal retrieval hook needed for Phase 7 validation:

- approved/edited canonical decisions are high-authority retrievable records,
- retrieval can prioritize approved decisions above stale/conflicting source
  evidence,
- stale/superseded evidence remains visible as background context when cited,
- rejected/marked unresolved/proceed-with-warning-only records are not treated
  as canonical truth.

If full chunking/indexing of canonical decisions is too large, add a narrow
adapter that lets Phase 5 retrieval include approved canonical decisions as a
candidate source with citations. Phase 4-style chunking of canonical decisions
can be deepened later.

## Event Publication

Publish `canonical_decision.approved` after a human approves or edits a
canonical decision.

Envelope rules:

- `subject.type=canonical_decision`,
- `subject.id` is the canonical decision ID,
- `causation.retrieval_request_id` is set when available,
- `versions` includes the decision version when represented,
- payload includes small metadata only: action, status, scope type, operation.

Never include decision text, rationale, evidence snippets, source names, URLs,
file names, actor secrets, or hidden source IDs in event payloads.

## Trust And Safety Rules

- Agent-only calls cannot approve canonical memory.
- Approval requires a human `actor_id`.
- Every approved/edited canonical decision must cite an evidence pack or source
  citations.
- Deleted source content must not be reproduced from stale decision metadata.
- Canonical decision text is customer content and must not be logged.
- Approval records should keep enough audit metadata to explain who did what and
  when.

## Acceptance Criteria

Phase 7 is complete when:

- `canonical_decisions` and `approval_records` have records and migrations.
- `propose_canonical_decision` creates `needs_review`, never approved.
- `approve_canonical_decision` requires a human actor.
- Approved and edited decisions preserve approval metadata.
- Proceed-with-warning, reject, mark-unresolved, and stop are auditable but do
  not create approved canonical memory.
- Superseding an approved decision marks the old one superseded.
- Approved decisions appear in future retrieval above stale/conflicting evidence.
- `canonical_decision.approved` is pointer-only and content-free.
