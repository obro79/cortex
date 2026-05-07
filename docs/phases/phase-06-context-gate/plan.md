# Phase 6 Plan: Context Gate

## Goal

Return a compact, cited `allow`, `warn`, or `block` decision over an evidence
pack before an agent starts risky implementation work.

Phase 6 starts where Phase 5 stops:

```txt
check_context_gate
  -> retrieve or load evidence_pack
  -> classify task risk
  -> detect conflicts, staleness, missing context, and permission ambiguity
  -> context_gate_result
  -> compact cited gate message
  -> context_gate.completed
```

The gate must be narrow, deterministic, and explainable. It should block only
high-confidence, high-impact ambiguity in v1.

## Inputs

- [`../implementation-roadmap.md`](../implementation-roadmap.md#phase-6-context-gate)
- [`../../architecture/v1-entity-state-schema.md`](../../architecture/v1-entity-state-schema.md#context_gate_results)
- [`../../architecture/pipeline-event-envelope.md`](../../architecture/pipeline-event-envelope.md)
- [`../../architecture/adrs/005-hybrid-retrieval-stack/config-and-tuning.md`](../../architecture/adrs/005-hybrid-retrieval-stack/config-and-tuning.md)
- [`../../architecture/adrs/009-source-allowlist-permissions-v1/README.md`](../../architecture/adrs/009-source-allowlist-permissions-v1/README.md)
- [`../phase-05-retrieval-evidence-packs/plan.md`](../phase-05-retrieval-evidence-packs/plan.md)
- [`../../../config/retrieval-v1.yaml`](../../../config/retrieval-v1.yaml)

## Existing Foundation

Earlier phases provide:

- `EvidencePack` records with citations, stale/conflict/missing/permission
  summaries,
- `RetrievalRequest` records with task hints and source allowlist snapshot hash,
- `ContextGateResult` Pydantic contract and `ContextGateStatus`,
- MCP tool name `check_context_gate`,
- source allowlist safety constraints,
- versioned `context_gate` config in `retrieval-v1.yaml`.

## Non-Goals

- No human approval persistence; Phase 7 owns approval records and canonical
  decisions.
- No automatic canonical memory creation.
- No LLM-based risk classifier or answer synthesis.
- No provider-native ACL snapshots beyond Phase 5 source allowlist safety.
- No retrieval/index changes.
- No broad policy engine; use explicit v1 categories and deterministic rules.

## Architecture

```txt
ContextGateService
  -> check_context_gate(args)
      -> load or create evidence_pack via RetrievalService
      -> RiskClassifier
      -> EvidenceSignalExtractor
          -> conflicts
          -> stale context
          -> missing context
          -> permission ambiguity
      -> GateDecisionEngine
      -> ContextGateResultRepository.create()
      -> GateMessageRenderer
      -> ContextGatePublisher.context_gate.completed
```

Gate decisions must cite evidence pack citations. Do not cite hidden or
non-allowlisted sources.

## Proposed Module Layout

```txt
src/cortex/context_gate/
  __init__.py
  config.py
  risk.py
  signals.py
  decision.py
  render.py
  service.py
  publishers.py

tests/context_gate/
tests/mcp/test_check_context_gate.py
```

Keep rules readable and deterministic. If a rule becomes unclear, prefer an
explicit table or function over a clever score.

## Config

Use `config/retrieval-v1.yaml` through the typed retrieval config loader.

Phase 6 uses the `context_gate` section:

```txt
gate_version = gate-v1
high_confidence_conflict_threshold = 0.80
stale_context_days = 90
min_required_sources_for_high_risk_tasks = 2
block_on_permission_uncertainty = true
block_on_high_confidence_architecture_conflict = true
warn_on_missing_low_risk_context = true
```

The loader should reject missing gate config, invalid thresholds, negative day
counts, invalid source counts, and unversioned gate config.

## Data Model

Add `context_gate_results` SQLAlchemy record and migration.

Fields, indexes, and lifecycle states should match
`v1-entity-state-schema.md`.

Required lifecycle:

```txt
evaluating -> allow
           -> warn
           -> block -> resolved
           -> failed
```

Phase 6 may store `resolved_at`/`resolution_action` fields but should not
implement human resolution actions. Phase 7 owns those workflows.

## Risk Classifier

Classify the task/evidence risk category from:

- task hints,
- query text,
- Linear/GitHub issue IDs,
- file paths,
- source coverage,
- evidence claims and conflict summaries.

First categories:

- `architecture_conflict`,
- `stale_context`,
- `permission_sensitive_ambiguity`,
- `missing_task_context`,
- `migration_billing_infra_deletion_data_access`,
- `low_risk_ambiguity`,
- `clear_context`.

Classifier rules should be deterministic in Phase 6. No LLM classifier.

## Evidence Signals

Extract gate signals from the evidence pack:

- high-confidence conflicting claims,
- stale docs versus newer Slack/GitHub/Linear evidence,
- permission ambiguity or permission exclusion that affects the task,
- missing referenced Linear/GitHub task context,
- insufficient source coverage for high-risk categories,
- clear current evidence with no conflict.

Every warn/block signal must carry citation IDs that resolve within the evidence
pack. If a signal cannot cite evidence, it should not block; use `failed` or
`warn` depending on risk and permission ambiguity.

## Decision Rules

Decision priority:

1. `failed`: evidence pack missing, invalid, uncited, or permission safety cannot
   be evaluated.
2. `block`: permission ambiguity when
   `block_on_permission_uncertainty=true`.
3. `block`: high-confidence architecture conflict when
   `block_on_high_confidence_architecture_conflict=true`.
4. `block`: high-risk task has fewer than
   `min_required_sources_for_high_risk_tasks` allowlisted sources.
5. `warn`: low-risk ambiguity or missing low-risk context when configured.
6. `allow`: current, cited, non-conflicting evidence is sufficient.

Blocks must include required human actions:

- approve,
- edit,
- proceed with warning,
- mark unresolved,
- stop.

These are instructions for the agent/human; Phase 7 persists the actual human
action.

## MCP Tool

Implement `check_context_gate`.

Inputs:

- query/task text,
- optional `retrieval_request_id`,
- optional `evidence_pack_id`,
- task hints,
- source filters.

Behavior:

- if `evidence_pack_id` is supplied, evaluate that pack,
- otherwise call Phase 5 retrieval to create an evidence pack,
- return `ContextGateResult` structured JSON plus compact text,
- include `allow`, `warn`, `block`, or `failed`,
- include cited reasons and required actions where relevant.

Tool output must not expose non-allowlisted source names, URLs, file names,
snippets, chunk IDs, or debug IDs.

## Event Publication

Publish `context_gate.completed` after durable gate result creation.

Envelope rules:

- `subject.type=context_gate_result`,
- `subject.id` is the gate result ID,
- `causation.retrieval_request_id` is set,
- `versions.gate_version` is set,
- payload includes small metadata only: status, risk category, and operation.

Never include evidence snippets, query text, hidden source identifiers, required
action prose, or secrets in event payloads.

## Evaluation

Add gate eval cases:

- COR-123 conflict fixture returns `block`,
- low-risk ambiguity returns `warn`,
- clear current evidence returns `allow`,
- permission ambiguity returns `block` when configured,
- missing high-risk task context returns `block`,
- uncited conflict does not block.

Metrics:

- gate accuracy,
- conflict detection accuracy,
- permission safety,
- citation coverage for warn/block,
- latency,
- compact output token count.

## Acceptance Criteria

Phase 6 is complete when:

- `context_gate_results` has a SQLAlchemy record and migration.
- `check_context_gate` returns structured JSON and compact cited text.
- Conflict fixtures return `block`.
- Low-risk ambiguity returns `warn`.
- Clear current evidence returns `allow`.
- Permission ambiguity fails closed according to config.
- Every warn/block reason cites evidence.
- `context_gate.completed` is pointer-only and content-free.
