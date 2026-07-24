# 03 — Agent checkpoint ingestion plan

## Outcome and boundary

Implement an opt-in Claude Code checkpoint exporter plus authenticated
`POST /v1/agent-checkpoints` ingestion. It turns a safe, bounded structured
checkpoint into one `RawEventInput(provider="agent_session")` and uses the
existing ingestion pipeline. It never accesses native Claude sessions, session
handles, raw transcripts, credentials, or provider API tokens.

Normal cadence is 50 completed messages or 15 minutes; demo cadence is three
completed messages or 30 seconds. A supported Claude Code `Stop` hook triggers
evaluation and a final flush. The final assistant message and safe local Git
metadata are the only local inputs; the exporter does not parse, upload, or
persist transcript content.

## Reuse and decisions

Reuse `AgentCheckpointExport`, including its explicit export marker, bounded
sections, content hash, transcript/session-handle/secret rejection, sensitive
file handling, and `to_payload()` conversion. Reuse trusted local API auth,
the existing `RawEventIngestionService`, canonical agent-session normalizer,
outbox, workers, chunking, embedding profile, Qdrant adapter, permissions, and
redacted run reports. Do not add a second checkpoint datastore or direct
normalization/indexing route.

The exporter owns only a local state file with: hashed local session reference,
completed-message count, last-flush timestamp, and last exported content hash.
It is mode `0600`, resides under the explicitly configured workspace-local
Cortex state directory, and never contains the native session ID or response
body. The hash may be computed locally from a local session reference supplied
by the supported hook but that reference is never sent; API payload includes
only `local_session_ref_hash` through `to_payload()`.

## Exact API contract

```text
POST /v1/agent-checkpoints
Authentication: trusted local Cortex credential
Body: AgentCheckpointImportEnvelope (strict; no extra fields)
201 Created | 200 Duplicate
{
  checkpoint_id: string,
  ingestion_status: "published" | "pending_retry",
  duplicate: boolean,
  trace_id: string
}
```

`AgentCheckpointImportEnvelope` is the safe serialized output of
`AgentCheckpointExport.to_payload()`: it contains the explicit export marker,
`export_enabled=true`, `local_session_ref_hash`, `content_hash`, and the
structured checkpoint body. It never contains `local_session_ref`, a native
session ID, transcript path, transcript content, or control handle.

The handler obtains actor and workspace authority exclusively from the trusted
local credential. It ignores/rejects body tenancy fields and has no provider
credential fields. It validates the safe import envelope before any persistence,
then maps it to the same `RawEventInput` identity already used by the existing
agent-checkpoint import plan:

```text
workspace_id = authenticated workspace
source_connection_id = configured Cortex agent-checkpoint connection for that workspace
provider = "agent_session"
external_event_id = "agent_checkpoint:{sha256(checkpoint_id:content_hash)}"
event_type = "agent_session.checkpoint.exported"
external_object_key = "agent_session:checkpoint:{checkpoint_id}"
idempotency_key = "agent_session:{workspace_id}:{checkpoint_id}:{content_hash}"
occurred_at = trusted request receipt time (unless safe export contract grows a timestamp)
trace_id = request trace
```

Duplicate means the existing workspace/idempotency record has the same payload
hash and returns its status without republishing. Same checkpoint ID or
idempotency key with a different hash is `409`; malformed/unsafe/oversized
content is `422`; absent/invalid auth is the existing `401/403`. Publish
failure is represented as `pending_retry`, maintains durable retry semantics,
and must not cause the exporter to generate a different checkpoint ID.

Visibility defaults to `private`. Workspace visibility needs a separately
recorded, explicit workspace opt-in and uses existing permission scopes during
retrieval. No hook flag, request body value, or browser caller may elevate
visibility or workspace authority.

## Exporter flow

1. `cortex checkpoint install --workspace PATH --mode normal|demo` installs the
   MCP configuration and a supported `Stop` hook for that workspace, creates
   protected state, stores trusted local auth without printing it, and writes
   thresholds. It must be idempotent and show a non-secret status summary.
2. On each eligible lifecycle event, read hook metadata and the final assistant
   message. Increment the local completed-message count only for completed
   messages. Derive summary, decisions, files, commands/tests, and next action
   from that message plus allowed Git metadata (`git diff --name-only`, branch,
   and focused test command/result if supplied safely).
3. Exclude sensitive paths before building `CheckpointFileSummary`; redact or
   reject secrets; disallow forbidden keys. Build `AgentCheckpointExport` with
   a stable checkpoint ID and hash. Do not use the hook's native session ID as
   payload, checkpoint ID, or log field.
4. Flush when count threshold or elapsed time threshold is met; reset counters
   only after a successful/deduplicated response. On `Stop`, attempt final
   flush even below threshold. Network failure retains the same export/hash and
   schedules bounded retry with jitter.
5. The API ingests it through `RawEventIngestionService`; workers normalize,
   chunk, embed, index, and permission-filter it like every other source.

The demo installer is the sole way to select 3/30s; it writes an explicit
`demo=true` local configuration and prints a warning that it is unsuitable for
normal use. No remote request selects demo thresholds.

## Tickets

1. **COR-CHK-301 — Local exporter/state.** Implement structured final-message
   extraction, protected hash-only state, normal/demo threshold scheduler,
   final flush, stable retry, and non-secret diagnostics.
2. **COR-CHK-302 — Claude Code hook/install command.** Generate supported
   workspace-local Stop-hook configuration and MCP registration; make install,
   status, and uninstall idempotent without exposing credentials.
3. **COR-CHK-303 — Checkpoint API route.** Add strict authenticated endpoint,
   authority resolution, existing-contract validation, RawEventInput mapping,
   duplicate/conflict response mapping, and trace propagation.
4. **COR-CHK-304 — Permission/visibility integration.** Bind source connection
   and private/workspace visibility to existing scopes; prove no body override.
5. **COR-CHK-305 — Pipeline/evidence test.** Exercise checkpoint through
   normalize/chunk/embed/Qdrant/retrieval and assert its prior-agent provenance.

## Validation and acceptance

- Unit-test 50/15m and 3/30s thresholds, timer reset, final flush, no flush for
  incomplete lifecycle metadata, retries, same-hash dedupe, and content-change
  conflict.
- Unit-test forbidden transcript/message/session/control-handle keys, secrets,
  sensitive files, blank/oversized fields, and logs/state redaction.
- API-test trusted authority, missing/invalid auth, no body workspace authority,
  no visibility elevation, 201/200/409/422 mappings, and trace IDs.
- Integration-test a valid export to a source object/chunk/embedding/Qdrant
  point and permission-filtered MCP task context; test private, workspace,
  cross-workspace, missing-scope, and revoked-scope cases.
- Acceptance demo: after three completed messages or 30 seconds, a safe
  checkpoint is published; an end-of-session flush occurs; the final answer can
  cite its prior-agent evidence without reproducing a transcript.

## Safety and truth boundaries

Cortex receives an approved structured export, not Claude Code state. It must
not inspect, resume, fork, control, discover, or otherwise access a native
Claude session. Raw transcripts, native identifiers, session/resume/fork
handles, private source paths, credentials, and secrets must be rejected before
network transmission and omitted from state, logs, API responses, reports, and
demo assets. The initial COR-123 checkpoint remains an imported demo snapshot;
automatic export shown in the intro is an explicit structured export, not proof
of access to a native session.
