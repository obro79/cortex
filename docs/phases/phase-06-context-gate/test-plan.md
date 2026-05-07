# Phase 6 Test Plan

## Commands

```bash
ruff check .
ruff format --check .
mypy src
pytest
```

Focused local loop:

```bash
pytest tests/context_gate tests/mcp tests/retrieval tests/dev
```

## Coverage Map

```txt
Config
  -> context_gate YAML defaults match ADR
  -> typed loader rejects invalid thresholds/counts/versions

Persistence
  -> context_gate_results lifecycle
  -> retrieval/evidence foreign IDs stored
  -> gate_version recorded
  -> hidden source IDs not stored in reasons/actions

Risk classifier
  -> architecture conflict
  -> stale context
  -> permission-sensitive ambiguity
  -> missing task context
  -> migration/billing/infra/deletion/data-access
  -> low-risk ambiguity
  -> clear context

Evidence signals
  -> conflicts require citations
  -> stale context detected
  -> permission ambiguity detected
  -> missing context detected
  -> source coverage evaluated

Decision engine
  -> COR-123 conflict blocks
  -> low-risk ambiguity warns
  -> clear evidence allows
  -> permission ambiguity blocks
  -> missing high-risk context blocks
  -> uncited conflict does not block

MCP tool
  -> check_context_gate with evidence_pack_id
  -> check_context_gate creating evidence pack through retrieval
  -> structured errors
  -> no hidden source leakage

Events/evals
  -> context_gate.completed envelope
  -> gate accuracy
  -> citation coverage for warn/block
  -> compact output token count
```

## Tests To Create

| Test file | Assertions |
| --- | --- |
| `tests/context_gate/test_gate_config.py` | Gate config defaults match ADR and invalid values fail validation. |
| `tests/context_gate/test_context_gate_repository.py` | Lifecycle, links, gate version, safe reasons/actions JSON. |
| `tests/context_gate/test_risk_classifier.py` | Risk categories from query/task/file/evidence hints. |
| `tests/context_gate/test_signal_extractor.py` | Conflict, stale, missing, permission, and coverage signals with citations. |
| `tests/context_gate/test_decision_engine.py` | Block/warn/allow/failed priority rules. |
| `tests/context_gate/test_message_renderer.py` | Compact cited output and required actions without hidden source leakage. |
| `tests/context_gate/test_context_gate_publisher.py` | Exact `context_gate.completed` envelope and forbidden payload protection. |
| `tests/mcp/test_check_context_gate.py` | MCP success/error paths with supplied or created evidence pack. |
| `tests/context_gate/test_gate_evals.py` | COR-123 block, low-risk warn, clear allow, permission block, missing context block. |

## Golden Assertions

COR-123 conflict:

```json
{
  "status": "block",
  "risk_category": "architecture_conflict"
}
```

Required block actions:

```json
["approve", "edit", "proceed_with_warning", "mark_unresolved", "stop"]
```

Minimum MCP response:

```json
{
  "ok": true,
  "context_gate_result_id": "gate_...",
  "status": "block",
  "text": "compact cited gate message",
  "result": {}
}
```

Warn/block results must cite evidence. Event payloads must not contain evidence
snippets, query text, hidden source identifiers, required action prose, or
secrets.

## Not Required In Phase 6

- approval record persistence,
- canonical decision creation,
- LLM risk classification,
- Slack approval bot,
- browser tests,
- provider-native ACL tests.
