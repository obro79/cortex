# Phase 7 Test Plan

## Commands

```bash
ruff check .
ruff format --check .
mypy src
pytest
```

Focused local loop:

```bash
pytest tests/canonical_memory tests/mcp tests/retrieval tests/context_gate
```

## Coverage Map

```txt
Persistence
  -> canonical_decisions lifecycle
  -> approval_records append-only audit
  -> supersession links
  -> decision text/rationale not logged

Proposal
  -> context gate result input
  -> evidence pack input
  -> scope derivation
  -> citation validation
  -> needs_review only

Approval
  -> approve
  -> edit
  -> proceed_with_warning
  -> mark_unresolved
  -> reject
  -> stop
  -> supersede
  -> human actor required
  -> agent-only approval rejected

Retrieval integration
  -> approved decision appears in future retrieval
  -> edited decision appears with approval metadata
  -> stale/superseded evidence visible but lower ranked
  -> rejected/unresolved/proceed-warning-only not canonical truth

MCP tools
  -> propose_canonical_decision success/error
  -> approve_canonical_decision success/error
  -> structured validation failures

Events
  -> canonical_decision.approved envelope
  -> pointer-only payload
```

## Tests To Create

| Test file | Assertions |
| --- | --- |
| `tests/canonical_memory/test_canonical_decision_repository.py` | Lifecycle, status transitions, supersession links, no content logs. |
| `tests/canonical_memory/test_approval_record_repository.py` | Append-only approval records and indexes. |
| `tests/canonical_memory/test_proposal_service.py` | Evidence/citation validation, scope derivation, `needs_review` only. |
| `tests/canonical_memory/test_approval_service.py` | Approve/edit/proceed-warning/mark-unresolved/reject/stop/supersede and human actor requirement. |
| `tests/canonical_memory/test_retrieval_priority.py` | Approved/edited decisions rank above stale evidence; rejected/unresolved records do not. |
| `tests/canonical_memory/test_canonical_publishers.py` | Exact `canonical_decision.approved` envelope and forbidden payload protection. |
| `tests/mcp/test_propose_canonical_decision.py` | MCP proposal success/error shape. |
| `tests/mcp/test_approve_canonical_decision.py` | MCP approval success/error shape and agent-only rejection. |

## Golden COR-123 Assertions

Proposal:

```json
{
  "status": "needs_review",
  "title": "Session storage canonical decision"
}
```

Approval:

```json
{
  "action": "approve",
  "status": "approved",
  "approved_by_actor_id": "human_..."
}
```

Edited approval:

```json
{
  "action": "edit",
  "status": "edited",
  "original_text": "...",
  "final_text": "Postgres is the future session source of truth; Redis fallback remains until COR-119 is resolved."
}
```

Future retrieval should return the approved/edited decision before stale Redis
docs while still citing the historical evidence that caused the conflict.

## Not Required In Phase 7

- Slack approval bot,
- web approval UI,
- LLM proposal generation,
- provider-native identity integration,
- source deletion implementation,
- full canonical-decision chunking rebuild pipeline if a narrower retrieval
  hook satisfies validation.
