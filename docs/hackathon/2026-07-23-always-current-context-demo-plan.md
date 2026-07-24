# Cortex: Always-Current Context Demo Plan

**Status:** Approved implementation plan

**Date:** 2026-07-23

**Target:** A polished three-minute hackathon demo built in a 24-hour execution window

**Thesis:** Always-current context for every agent

## Summary

The hero demo is a two-developer handoff during the `COR-123` session incident:

1. Developer A investigates session logouts in Claude Code.
2. An explicitly installed Cortex hook automatically publishes a redacted,
   structured checkpoint.
3. A new synthetic Slack message is posted live and indexed through the real
   Slack-to-Cortex path.
4. Developer B opens Claude Code and asks Cortex to pick up the incident.
5. Cortex combines the prior agent checkpoint with fresher Slack, GitHub, Jira,
   email, and Drive evidence.
6. Claude identifies the stale Redis fallback, cites the supporting evidence,
   names the next file and test, and waits for approval before editing.
7. The Cortex UI proves freshness by animating the new Slack node into a
   task-scoped evidence graph.

Only Slack is live during the final acceptance run. GitHub, Jira, email,
Drive/docs, and the initial agent checkpoint are deterministic imported
snapshots. Every visible source is labelled `Live` or `Demo snapshot`.

The opening 20-second video contains Developer A's checkpoint and the
source-convergence montage. The live stage sequence begins with the Slack
update, Developer B's Claude Code request, and the evidence-graph reveal.

## Current State

### Built and reusable

- Slack OAuth, selected channels, signed webhooks, backfill, cursors, health,
  and SQL persistence.
- Canonical raw-event, normalization, chunking, embedding, relationship, and
  indexing contracts.
- Hosted-Qdrant adapter and one shared embedding/index profile.
- Durable permission scopes and permission-filtered task-context retrieval.
- MCP `get_task_context` proxy for Claude Code and other existing agents.
- Structured `AgentCheckpointExport` contract that rejects transcripts, native
  session handles, secrets, and sensitive paths.
- Redacted demo-run reports with ingestion, vector, query, and evidence counts.
- Next.js Context, Evidence, Health, and MCP control-plane screens.
- Existing COR-123 fixtures, presentation generator, screenshots, and video
  packaging structure.
- Cortex light/dark palette and semantic warning colors.

### Missing

- Claude Code hook exporter and authenticated checkpoint-ingestion route.
- One coherent six-source incident corpus.
- A credentialed Slack-to-hosted-Qdrant acceptance run.
- Task evidence graph API and presentation UI.
- Connector-card animation and dedicated demo route.
- Updated intro video, four-slide deck, pitch, screenshots, and rehearsed
  three-minute run.

## Demo Truth Boundary

- Slack is the sole live provider in this demo.
- GitHub, Jira, email, Drive/docs, and the initial agent checkpoint are imported
  snapshots.
- Connector-card `Consume` actions are presentation state for content already
  indexed by the operator setup command. They are not OAuth or ingestion claims.
- Cortex exports approved structured checkpoints. It does not resume, fork,
  inspect, or control another person's native Claude session.
- Raw transcripts, native session identifiers, provider credentials, and raw
  Qdrant payloads must never enter reports, browser responses, logs, or assets.
- If a live dependency fails, the recovery path must be visibly labelled as a
  prerecorded or simulated fallback.

## Golden COR-123 Incident Corpus

Use one deterministic timeline with a distinct role for every source:

| Source | Mode | Evidence role |
| --- | --- | --- |
| GitHub | Demo snapshot | The rollout PR moves session reads to Postgres and identifies the affected middleware. |
| Drive/docs | Demo snapshot | An older rollout document still permits Redis fallback and is explicitly stale. |
| Email | Demo snapshot | A support escalation establishes customer impact and incident timing. |
| Jira | Demo snapshot | The incident ticket records severity, deployment version, and owner. |
| Claude Code checkpoint | Demo snapshot in the opening video | Developer A records the suspected fallback path, inspected file, test result, unresolved question, and next action. |
| Slack | Live synthetic channel | The newest message confirms that pods with Redis fallback enabled are invalidating sessions. |

Add a small tracked incident-service fixture containing the exact middleware
file and focused test named by the evidence. Developer B's Claude session runs
inside this fixture so the returned next action is inspectable and real.

An operator-only preparation command must:

1. Validate Postgres, Kafka, hosted Qdrant, migrations, Slack configuration,
   selected channel, and the MCP proxy.
2. Seed the deterministic snapshot evidence.
3. Run it through canonical normalization, chunking, embedding, and indexing.
4. Verify the expected Qdrant points.
5. Record the initial agent checkpoint and redacted run report.
6. Be idempotent and exit nonzero if any required gate fails.

## Automatic Claude Code Checkpoints

Use Claude Code's supported command-hook lifecycle. A `Stop` hook receives
structured lifecycle metadata and the final assistant message. The local
exporter must not upload or parse transcript contents for the hackathon path.

### Scheduling policy

- Normal default: flush after 50 completed messages or 15 minutes, whichever
  happens first.
- Demo mode: flush after 3 completed messages or 30 seconds.
- Perform a final flush when the session ends.
- Store only a hashed local session reference, completed-message count,
  last-flush time, and last exported content hash.

### Export behavior

- Derive a bounded task summary, decisions, files, tests, and next actions from
  the final assistant response plus safe local Git metadata.
- Filter sensitive file paths.
- Run all content through the existing secret and checkpoint validators.
- Default visibility to private.
- Require explicit workspace opt-in for workspace-visible checkpoints.
- Use checkpoint IDs and content hashes for idempotent retries.
- Send only the validated structured payload to the Cortex API.

Provide one setup command that installs:

- the Cortex MCP server in Claude Code;
- the checkpoint hook for the prepared workspace;
- normal or demo threshold configuration;
- trusted local API authentication without printing the token.

## Backend Interfaces

### `POST /v1/agent-checkpoints`

Purpose: ingest one validated structured checkpoint through the shared pipeline.

Requirements:

- Resolve workspace and actor authority from trusted local authentication.
- Do not accept workspace authority or provider credentials in the body.
- Accept the existing safe checkpoint payload.
- Return checkpoint ID, ingestion status, duplicate status, and trace ID.
- Preserve existing transcript, secret, native-handle, and sensitive-path
  rejection behavior.

### `GET /v1/demo/tasks/{task_ref}/graph`

Purpose: return the task-scoped graph used by the presentation UI.

Response contract:

```text
TaskEvidenceGraph
  task_ref
  generated_at
  nodes[
    id
    kind: task | evidence
    provider
    label
    mode: live | imported_snapshot | fixture
    freshness
    source_updated_at
    citation_id?
  ]
  edges[
    id
    source
    target
    relationship
    state: supporting | conflicting
  ]
```

Requirements:

- Apply workspace and permission filtering before graph projection.
- Return safe evidence metadata only.
- Never include raw provider payloads, provider tokens, transcript content,
  private source URLs, or vector payloads.
- Add only this read-only route to the browser BFF allowlist.

### Operator command

Add `prepare_cortex_demo` as the single setup and verification entry point.
Snapshot seeding and checkpoint ingestion must not be callable from browser
code.

## Presentation UI

Add `/ui/demo` without replacing the existing diagnostic screens.

### Connector cards

- Slack, GitHub, Jira, email, Drive/docs, and Claude Code cards.
- Recognizable provider icons with accessible labels.
- Compact `Live` and `Demo snapshot` badges.
- `Consume` transitions pre-indexed snapshots into a connected presentation
  state.
- The full source-card sequence completes in approximately three seconds.
- The animation never implies that OAuth or ingestion happened on click.

### Task evidence graph

- Use a dependency-free, fixed-layout SVG.
- Center `COR-123`.
- Render one evidence node per contributing source.
- Use gold/fresh treatment for the new Slack evidence.
- Use bronze/conflict treatment for the stale Redis document.
- Give the prior Claude checkpoint a distinct agent-session treatment.
- Poll the graph endpoint once per second during the live window.
- Stop polling after the Slack node appears or after 45 seconds.
- Fade and pulse the new Slack node and edge when they arrive.
- Clicking a node opens a compact citation drawer containing source, mode,
  timestamp, freshness, excerpt, and evidence-pack link.

Do not build a global company graph, ingestion ticker, general chat surface, or
production connector administration in this slice.

## Claude Code Hero Request

Developer B submits:

> Pick up the COR-123 session incident. Use Cortex before changing anything.
> Tell me what Developer A established, what changed since then, the likely
> cause, conflicting evidence, and the safest next file and test to inspect.

The accepted response must:

- invoke `get_task_context`;
- cover all six source types;
- distinguish Developer A's checkpoint from the newer Slack update;
- identify the stale Redis documentation conflict;
- state the likely cause and customer impact;
- name the exact middleware file and focused test;
- include inspectable citations and freshness;
- stop before editing and request approval.

## Three-Minute Run of Show

| Time | Action |
| --- | --- |
| 0:00–0:20 | Play the source-convergence intro video, including Developer A's automatic checkpoint. |
| 0:20–0:35 | Present the thesis and problem slide. |
| 0:35–0:45 | Rapidly activate the six source cards and reveal the pre-indexed incident cluster. |
| 0:45–1:05 | Post the prepared synthetic Slack message in the real demo channel. |
| 1:05–1:20 | Return to Cortex and show the live Slack node fade into the COR-123 graph. |
| 1:20–2:15 | Developer B asks the prepared Claude Code question; Cortex returns the cited diagnosis and safe next action. |
| 2:15–2:35 | Open the Slack, prior-agent, and stale-doc nodes to prove provenance and freshness. |
| 2:35–2:50 | Show the architecture/proof slide. |
| 2:50–3:00 | Close on “Always-current context for every agent.” |

### Recovery path

- Keep the snapshot corpus and checkpoint preloaded.
- Keep a prerecorded Slack-node arrival available.
- If Slack delivery fails, use the signed webhook simulator and visibly label
  it as fallback.
- If Claude output drifts, use a captured MCP exchange with the same
  evidence-pack ID.
- Never replace a failed live claim with an unlabelled simulation.

## Slides, Video, and Pitch

### Four-slide deck

1. **Always-current context for every agent**
2. **The problem:** connectors search individual sources; Cortex continuously
   normalizes and indexes shared context.
3. **How it works:** sources → canonical event pipeline → Postgres/Qdrant →
   permission-filtered MCP context.
4. **Closing:** one context layer, every agent, no manual handoff.

### Twenty-second intro video

| Time | Visual |
| --- | --- |
| 0–3s | Thesis and Cortex title. |
| 3–8s | Six source cards stream events into Cortex. |
| 8–13s | Developer A's Claude work becomes an approved checkpoint. |
| 13–17s | The COR-123 evidence graph forms. |
| 17–20s | Developer B's terminal receives current context. |

Regenerate the deck, screenshots, narration, captions, storyboard, README demo
instructions, and one-page pitch from the final verified run.

## Test and Acceptance Plan

### Automated gates

- Hook threshold, timer, final flush, retry, deduplication, and local-state
  tests.
- Checkpoint rejection tests for transcripts, session handles, secrets,
  sensitive files, and oversized content.
- Agent checkpoint → normalization → chunk → embedding → Qdrant → MCP
  integration test.
- Slack signed event → canonical object → verified vector → graph-node
  integration test.
- Cross-workspace, missing-scope, revoked-scope, and stale-ACL denial tests.
- Graph payload-leak and workspace-isolation tests.
- Snapshot seed idempotency and report-count validation.
- Frontend lint, typecheck, production build, and browser verification.

### Demo acceptance

- Snapshot source-card animation completes within three seconds.
- Demo checkpoint exports after three messages or 30 seconds.
- The live Slack graph node appears within ten seconds of webhook receipt.
- The MCP answer cites all six source types and includes the new Slack evidence.
- The stale document is visibly marked conflicting.
- No raw transcript, provider token, native session handle, or private Slack
  content appears in logs or public artifacts.
- The complete performance finishes under three minutes in two consecutive
  rehearsals.

## 24-Hour Execution Order

| Window | Work |
| --- | --- |
| Hours 0–3 | Freeze the incident narrative, corpus, sample repo, seed manifest, and golden expected answer. |
| Hours 3–8 | Implement the checkpoint route, hook exporter, thresholds, redaction, setup command, and focused tests. |
| Hours 5–10 | Implement snapshot preparation, graph API, Slack-to-graph integration, and hosted-Qdrant preflight. |
| Hours 8–14 | Implement `/ui/demo`, source cards, SVG graph, citation drawer, and live-node polling. |
| Hours 12–18 | Rebuild the intro video, four-slide deck, pitch, screenshots, narration, and README. |
| Hours 18–21 | Run the credentialed Slack/Qdrant acceptance test and Claude Code MCP rehearsal. |
| Hours 21–24 | Fix demo-blocking defects, capture fallbacks, run two timed rehearsals, and freeze artifacts. |

Use four isolated workstreams with exclusive ownership:

1. checkpoint integration;
2. corpus and graph backend;
3. presentation frontend;
4. media and pitch assets.

Final integration, credentialed validation, artifact review, and rehearsal stay
centralized.

## Assumptions

- Slack app/channel access and hosted-Qdrant credentials will be supplied for
  the final acceptance run.
- The live Slack channel contains synthetic demo content only.
- The other five sources remain imported demo snapshots.
- Existing runtime-preflight and palette commits remain part of the working
  branch.
- The implementation optimizes for a trustworthy hackathon vertical slice,
  not production OAuth breadth or a general-purpose dashboard.
