# Cortex three-person demo sprint

**Duration:** 3 hours
**Objective:** deliver one honest, rehearsable `COR-123` proof: a Slack update
changes the evidence Cortex returns to a developer agent, with citations and no
claim that snapshot sources are live.

This is a deliberately narrow implementation slice of the
[hackathon build package](new_plan/README.md). It prioritizes a single reliable
demo path over general connector administration or production completeness.

## Demo finish line

At the end of the sprint, the operator can run a deterministic pre-update and
post-update `COR-123` walkthrough:

1. Cortex returns a cited context pack containing five imported snapshots and
   one imported Codex checkpoint.
2. A valid Slack event passes through the selected-source ingestion path.
3. The next task-context response includes that Slack evidence, identifies the
   stale Drive conflict, and changes the recommended next action.
4. The UI and all demo material visibly label Slack as `LIVE` only when the
   real configured path was used; all other sources remain `DEMO SNAPSHOT`.

## Ownership and worktree map

| Owner | Worktree | Exclusive scope | Integration contract |
| --- | --- | --- | --- |
| Slack owner | `cortex_2` | Signed Slack event acceptance, selected-source validation, durable ingestion handoff, and the post-update fixture/event path. | Emits a safe `SlackEvidence` record with `mode`, timestamp, citation ID, freshness, and trace ID. |
| Embeddings owner | `cortex_3` | Demo embedding/index readiness, deterministic retrieval of the COR-123 evidence, and pre/post evidence-pack evaluation. | Accepts canonical normalized events and publishes evidence-pack IDs plus ordered safe evidence metadata. |
| Codex-hook owner / integrator | `cortex_new` | Opt-in Codex checkpoint exporter, bounded checkpoint ingestion, task-context presentation contract, rehearsal command, and demo truth disclosure. | Emits an `AgentCheckpointExport`; consumes the evidence pack without exposing a transcript, native session handle, token, or raw source body. |

No owner edits another owner’s files without first agreeing on the contract.
The integrator may make a small compatibility adjustment during the final
integration window, but should not reimplement another workstream.

## Locked data contract

The three workstreams exchange safe, provider-neutral metadata. The browser,
MCP arguments, and fixture payloads never supply workspace or actor authority.

```text
EvidenceItem
  id, provider, mode, source_updated_at, freshness
  citation_id, approved_excerpt, relationship

TaskContext
  task_ref, evidence_pack_id, trace_id
  summary, recommended_next_action, evidence[]

AgentCheckpointExport
  task_ref, safe_summary, decisions, safe_file_refs
  test_refs, next_actions, content_hash
```

Required modes are `live` and `imported_snapshot`. A Slack event becomes
`live` only after the signed, selected-source path accepts it; a local simulator
or fallback must be labelled as such in the operator surface.

## Time-boxed execution plan

### 0:00–0:20 — Contract and baseline

All owners:

- confirm the existing `COR-123` fixture IDs, source labels, and safe excerpts;
- freeze the pre-update and post-update expected evidence order;
- run the local runtime preflight and record any dependency blockers;
- agree on one task-context fixture/response shape before parallel work begins.

### 0:20–1:45 — Parallel implementation

#### Slack owner

- Reuse the existing Slack webhook verification and selected-channel/source
  boundaries; do not add a second ingestion path.
- Add or complete the deterministic COR-123 Slack update that reaches the raw
  event pipeline with stable idempotency identity.
- Verify invalid signatures, unselected sources, and duplicate delivery are
  rejected or safely deduplicated.
- Provide one post-update event/evidence fixture for the integrator.

#### Embeddings owner

- Verify the selected demo embedding profile and index are ready before
  retrieval; fail closed rather than returning invented ranking data.
- Ensure the pre-update context includes the checkpoint plus the snapshot
  evidence and identifies the stale Drive item as conflicting.
- Ensure the post-update Slack evidence is retrieved as fresh evidence without
  displacing clearly relevant sources.
- Add a focused evaluator that asserts source modes, freshness ordering,
  citation IDs, and recommended-next-action change.

#### Codex-hook owner / integrator

- Build an explicit opt-in Codex hook/export command that produces only the
  bounded `AgentCheckpointExport` contract.
- Reject transcripts, session handles, secrets, and sensitive paths before
  ingestion; store only opaque/hash-based session references where needed.
- Make the checkpoint visible as an `imported_snapshot` evidence item in the
  COR-123 context pack.
- Prepare the operator command and a minimal display/readout of pre/post task
  context, evidence-pack ID, source mode, and trace ID.

### 1:45–2:20 — Contract integration

1. Slack owner supplies the accepted post-update event and expected metadata.
2. Embeddings owner runs it through retrieval and supplies the two verified
   evidence-pack outputs.
3. Codex-hook owner verifies the checkpoint is present before the update and
   that the post-update response changes only through verified new evidence.
4. Resolve only contract mismatches or demo-breaking failures; defer polish.

### 2:20–3:00 — Rehearsal and release evidence

- Run the operator flow twice from a clean local state.
- Confirm the pre-update output is cautious and the post-update output names
  the Redis fallback, stale Drive conflict, and safe next file/test.
- Capture the visible source-mode disclosure and post-update evidence pack.
- Record exact command output, evidence-pack IDs, and known fallback behavior
  in the run report.

## Acceptance checklist

- [ ] Pre-update task context contains the imported Codex checkpoint and five
      imported snapshot sources with citation IDs.
- [ ] A valid selected Slack event is accepted once and is idempotent on replay.
- [ ] Invalid signatures and unselected Slack sources are denied.
- [ ] Post-update context includes fresh Slack evidence and a new evidence-pack
      ID without leaking raw source payloads.
- [ ] The stale Drive source remains visible as a conflict rather than silently
      disappearing.
- [ ] Checkpoint export is opt-in and rejects transcript/session/secret data.
- [ ] All public/demo surfaces label real, snapshot, and fallback states
      truthfully.
- [ ] Two full rehearsals complete in under three minutes each.

## Explicit cuts

Do **not** spend this sprint on:

- OAuth expansion or live ingestion for GitHub, Jira, email, or Drive;
- hosted-Qdrant deployment work, broad embedding evaluation, or tuning;
- native Codex/Claude session resume, inspection, or control;
- general graph exploration, billing, SSO, or connector-admin UI;
- visual polish that does not help the operator prove the pre/post evidence
  change.

## Handoff notes

If the live Slack path cannot be completed, keep the post-update run clearly
marked `SIMULATED FALLBACK` and preserve the rejection/preflight evidence. Do
not relabel it as live. The next sprint begins with the recorded blocker,
reproduction command, and the last accepted evidence-pack IDs.
