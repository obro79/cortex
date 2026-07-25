# Phase 6 Implementation Checklist

## 1. Config

- Add `context_gate` defaults to `config/retrieval-v1.yaml`.
- Extend the typed config loader for gate settings.
- Validate gate version, thresholds, day counts, source counts, and boolean
  flags.

Acceptance:

- YAML defaults match ADR-005,
- invalid gate config fails validation,
- gate results record `gate_version`.

## 2. Persistence

- Add `ContextGateResultRecord`.
- Add migration and indexes from `v1-entity-state-schema.md`.
- Add repository methods for evaluating, allow, warn, block, failed, and
  resolved state.

Acceptance:

- lifecycle transitions are enforced,
- result rows link retrieval request and evidence pack IDs,
- reasons/actions JSON does not include hidden source identifiers.

## 3. Risk Classifier

- Implement deterministic risk categories:
  - architecture conflict,
  - stale context,
  - permission-sensitive ambiguity,
  - missing task context,
  - migration/billing/infra/deletion/data-access,
  - low-risk ambiguity,
  - clear context.
- Use task hints, query text, file paths, issue/PR IDs, source coverage, and
  evidence summaries.

Acceptance:

- broad risky paths classify high-risk,
- COR-123 classifies architecture conflict,
- low-risk ambiguity remains warn-eligible.

## 4. Evidence Signal Extractor

- Extract conflicts, stale evidence, missing context, permission ambiguity, and
  source coverage from evidence packs.
- Require citations for warn/block signals.
- Treat uncited high-impact signals as failed or warn according to risk.

Acceptance:

- every warn/block signal resolves citations,
- stale Redis versus newer Postgres evidence is detected,
- permission exclusions affecting the task are detected.

## 5. Decision Engine

- Implement priority rules from [`plan.md`](plan.md).
- Fail closed on permission ambiguity when configured.
- Block high-confidence architecture conflicts.
- Warn on low-risk ambiguity.
- Allow clear, current, cited evidence.

Acceptance:

- conflict fixtures block,
- low-risk ambiguity warns,
- clear current evidence allows,
- uncited conflict does not block.

## 6. Message Renderer

- Render compact agent-facing gate output.
- Include status, reason, cited evidence, and required human actions for blocks.
- Avoid hidden source identifiers and non-allowlisted content.

Acceptance:

- block message is compact and actionable,
- warn/allow messages are cited,
- output token count is bounded.

## 7. MCP Tool

- Implement `check_context_gate`.
- Accept existing evidence pack IDs or create a new pack through retrieval.
- Return structured JSON plus compact text.

Acceptance:

- supplied evidence pack path works,
- retrieval-created evidence pack path works,
- unknown args fail with structured errors.

## 8. Event Publisher

- Publish `context_gate.completed` after durable result creation.
- Include subject, causation, gate version, status, risk category, trace, and
  small metadata only.

Acceptance:

- exact envelope tests pass,
- event payload contains no evidence snippets, query text, required action prose,
  hidden source identifiers, or secrets.

## 9. Evals And Tests

- Add focused tests listed in [`test-plan.md`](test-plan.md).
- Keep Phase 5 golden retrieval tests in the focused loop.

Acceptance:

- `ruff check .` passes.
- `ruff format --check .` passes.
- `mypy src` passes.
- `pytest` passes.

## Completion Criteria

Phase 6 is complete when:

- gate results are durable and cited,
- `check_context_gate` is implemented,
- allow/warn/block/failed behavior is deterministic,
- permission ambiguity fails closed,
- blocks include required human actions,
- Phase 7 can persist the human resolution workflow.
