# 02 — Golden COR-123 incident backend plan

## Outcome and boundaries

Deliver one deterministic, permission-scoped COR-123 corpus that establishes
the demo diagnosis without fabricating a live integration. The corpus has
exactly **18 source records**: six decisive records (one from each source) and
12 clearly non-decisive distractors. GitHub, Jira, email, Drive/docs, and the
agent checkpoint are `imported_snapshot`; Slack is `live` only after its signed
webhook is accepted. A small Python incident-service fixture supplies the
middleware file and focused test named by the evidence.

This slice adds no browser ingestion endpoint, OAuth work, global graph, native
Claude-session access, or raw transcript storage. The graph read model/API is
backend work here; its visual presentation is explicitly a later/UI workstream.

## Reuse and architecture decisions

Use the existing `RawEventInput` → `RawEventIngestionService` → raw-event
outbox/Kafka → normalization → source object → chunk → embedding → Qdrant
pipeline. Each fixture importer creates a real `RawEventInput`; it may not
write source objects, chunks, embeddings, Qdrant points, or graph rows directly.
Use the existing normalizer registry: `github`, `jira`, `google_drive`,
`agent_session`, and `slack`; add/use a bounded offline-email snapshot adapter
only if an existing provider is not suitable. Snapshot content must retain its
real provider label and must never masquerade as `fixture`.

Postgres remains canonical for records, source metadata, relationships,
permissions, and graph projection. Local Compose Qdrant is the fast developer
target; the existing Qdrant adapter/profile remains the sole vector interface
and the operator preflight runs the same seed/query/count contract against
hosted Qdrant before the final rehearsal. No environment-specific schema,
embedding profile, or retrieval branch is allowed.

## Corpus contract

The frozen implementation manifest is
`fixtures/golden_incident/manifest.json`. Its validated model and
`RawEventInput` conversion live in `src/cortex/demo/golden_incident.py`.
That conversion is the offline rehearsal path: its pending Slack transition is
durably labelled `simulated_fallback`. A signed native Slack webhook remains
the only path that may produce evidence described as live.

Create a tracked Python fixture package and a versioned manifest, for example
`src/cortex/dev/cor123/` and `tests/fixtures/cor123/manifest.json`. The manifest
is the source of truth for count, stable identity, timestamps, source mode,
expected relationships, expected citation ID, and the golden evidence contract.
Every record must have a stable external event ID and an idempotency key derived
from `cor123-v1`, provider, and record ID. All synthetic content is explicitly
marked `synthetic_demo=true` in its safe metadata.

| Decisive source | Mode | Required fact | Stable task link |
| --- | --- | --- | --- |
| GitHub rollout PR | imported snapshot | session reads moved to Postgres; names middleware | `COR-123` |
| Drive rollout document | imported snapshot | old Redis-fallback guidance; marked conflicting/stale | `COR-123` |
| Support email | imported snapshot | customer logout impact and timeline | `COR-123` |
| Jira incident | imported snapshot | severity, deploy version, owner | `COR-123` |
| Claude checkpoint | imported snapshot | prior hypothesis, inspected file/test, unresolved question, next action | `COR-123` |
| Slack message | live after receipt | fallback-enabled pods invalidate sessions | `COR-123` |

The remaining 12 distractors are two per source. They must be plausible but
cannot assert the causal chain, override the six decisive facts, or be returned
as mandatory golden citations. At least two are deliberately lexically similar
to test reranking (for example, an unrelated logout report and an older session
rollout discussion). Distractors keep the same workspace and authorized scope
to make the evaluation meaningful; separate denial tests cover isolation.

The Python fixture contains only synthetic code: a documented stale Redis
fallback in the named session middleware and one focused failing/regression test
whose exact paths are locked in the manifest. The evidence and golden answer
name those manifest paths, not an invented production repository path.

## Data flow and interfaces

### Import path

`prepare_cortex_demo seed` loads the manifest, validates its evidence contract,
builds provider-native payloads, and calls a single `Cor123Importer.ingest`
port. That port accepts `RawEventInput` and delegates to
`RawEventIngestionService.ingest`. The command waits through canonical worker
stages and validates persisted source objects/chunks/embeddings and expected
Qdrant point IDs. Re-running it returns the original raw-event IDs with
`created=false`; an identity/content mismatch is a hard failure.

The initial checkpoint uses `AgentCheckpointExport.to_payload()` and provider
`agent_session`, never a transcript-shaped payload. Slack does not seed its
decisive message: the import records a pending live-evidence expectation only.
For offline development and recovery, a signed webhook simulator may submit the
same synthetic Slack event through the real route; reports and UI inputs must
label it `simulated_fallback`, never `live`.

### Task graph read model

Add a projection service that takes an already authorized task-scoped evidence
pack plus relationship records and returns `TaskEvidenceGraph`:

```text
GET /v1/demo/tasks/{task_ref}/graph
TaskEvidenceGraph {
  task_ref, generated_at,
  nodes: [{ id, kind: task|evidence, provider, label,
            mode: live|imported_snapshot|fixture,
            freshness, source_updated_at, citation_id? }],
  edges: [{ id, source, target, relationship,
            state: supporting|conflicting }]
}
```

The route derives workspace and actor from existing request authentication;
`workspace_id`, provider tokens, raw payloads, native identifiers, and source
URLs are neither query nor response fields. It filters permissions before
retrieval and projection, uses safe citation metadata only, and returns no raw
vector payloads. It is read-only and is the only new browser-BFF allowlisted
backend route. `mode` comes from immutable source metadata; `freshness` is
calculated from `source_updated_at`/sync state, not from client clock input.

The projection is deterministic: one `task:COR-123` node, at most one evidence
node per contributing source object, and a stable sort by mode/freshness/source
time/id. The stale Drive record has a `conflicting` edge; supporting records
have `supporting` edges. The live Slack evidence replaces only the pending
expectation after a verified pipeline completion, never merely on webhook
receipt.

### Evidence-contract evaluation

Add a machine-readable golden expectation consumed by both seed validation and
an integration test. Given the hero request, retrieval must produce an
evidence pack that: covers all six providers; includes the newest Slack
citation after live ingestion; retains the checkpoint as prior-agent evidence;
marks the Drive item as conflicting; identifies customer impact, stale Redis
fallback, the locked fixture middleware path, and focused test; and has no
unapproved claim. The evaluator checks citation IDs, providers, mode,
freshness ordering, conflict relation, and required/forbidden answer markers;
it does not grade hidden chain-of-thought or accept prose without citations.

## Tickets

1. **COR-BE-201 — Manifest and fixture package.** Add the 18-record manifest,
   deterministic timestamps/IDs, synthetic Python incident service, and exact
   six decisive/12 distractor classification.
2. **COR-BE-202 — Canonical snapshot importer.** Map each snapshot record,
   including safe checkpoint export, to `RawEventInput`; add an offline-email
   snapshot normalizer/adapter only when needed and register it.
3. **COR-BE-203 — Idempotent demo preparation.** Add `prepare_cortex_demo
   seed` to drive the shared pipeline and assert Postgres/Qdrant artifacts in
   Compose and hosted parity mode.
4. **COR-BE-204 — Task evidence graph projection/API.** Implement authorized,
   safe graph projection and `GET /v1/demo/tasks/{task_ref}/graph` with a BFF
   allowlist entry; no UI implementation.
5. **COR-BE-205 — Evidence-contract evaluator.** Add golden retrieval,
   provenance, conflict, coverage, and forbidden-data assertions.

## Validation and acceptance

- Unit-test manifest schema/count (exactly 18, 6+12), IDs, timestamp ordering,
  source modes, relationship roles, and fixture path/test existence.
- Integration-test each imported record through `RawEventInput` and all
  canonical stages; assert expected source objects, chunks, embedding records,
  and Qdrant points. Re-run seed and assert no extra events/points.
- Run the same acceptance suite with Compose Qdrant and a credentialed hosted
  Qdrant profile; hosted failure blocks the live-demo claim but not local work.
- Test graph workspace isolation, missing/revoked scopes, payload-leak
  rejection, deterministic order, stale conflict edge, and that Slack appears
  only after verified processing.
- Test the evidence evaluator both before Slack (partial/missing-live expected)
  and after signed Slack completion (six-source pass).

Acceptance is met when one idempotent seed produces the 17 available snapshot
records (including the checkpoint and distractors), then a valid Slack event
produces the 18th record and a graph node within the agreed end-to-end target;
the six-source evidence contract passes with inspectable citations and no
forbidden material.

## Safety and truth boundaries

All source text is synthetic demo data. Only Slack may be described as live,
and only after signature verification plus pipeline completion. GitHub, Jira,
email, Drive, and the checkpoint retain `Demo snapshot` metadata everywhere.
The corpus may store only the structured checkpoint contract; it must not read,
store, derive from, or link to native Claude sessions, native session handles,
or raw transcripts. Logs/reports/API output redact or omit credentials, private
URLs, raw payloads, vector payloads, secrets, and sensitive paths.
