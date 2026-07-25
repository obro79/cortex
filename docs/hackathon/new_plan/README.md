# Cortex Hackathon Build Package

**Status:** Decision-complete planning package
**Date:** 2026-07-23
**Delivery window:** 24 hours
**Demo length:** 3 minutes
**Thesis:** Always-current context for every agent

This directory turns the approved demo direction into implementation-sized
plans. The documents share one truth boundary: Slack is the only live provider
in the final acceptance run; GitHub, Jira, email, Drive/docs, and the initial
Claude Code checkpoint are labelled imported demo snapshots.

## Reading order

1. [Product and demo brief](01-product-demo-brief.md)
2. [Golden incident backend](02-golden-incident-backend.md)
3. [Agent checkpoint ingestion](03-agent-checkpoint-ingestion.md)
4. [Presentation frontend](04-presentation-frontend.md)
5. [Live data, Slack, and Qdrant](05-live-data-slack-qdrant.md)
6. [Slides, video, screenshots, and pitch](06-demo-assets-slides-video-pitch.md)
7. [Execution tickets and acceptance](07-execution-tickets-and-acceptance.md)
8. [Ambiguity register and decisions](08-ambiguity-register-and-decisions.md)
9. [UI wireframes and interaction specification](09-ui-wireframes-and-interaction-spec.md)

The parent direction remains
[Always-Current Context Demo Plan](../2026-07-23-always-current-context-demo-plan.md).
If a detail conflicts, this package controls the next implementation slice and
the parent document controls the overall demo thesis.

## Locked decisions

- Hero: Developer B continues Developer A's `COR-123` incident investigation in
  Claude Code without a manual handoff document.
- Runtime: Compose Postgres plus local Qdrant first; the same operator contract
  must work with hosted Qdrant.
- Corpus: 189 records total, containing six decisive items, 30 near-misses,
  42 stale/conflicting historical records, 63 operational records, and 48
  unrelated records.
- Ingestion: every source enters through the shared raw-event pipeline; no
  direct SQL fixture insertion.
- Freshness proof: a signed Slack event changes the second evidence pack.
- Retrieval: normal hybrid fusion plus a bounded provider-diversity boost;
  original score provenance remains visible.
- Automated evaluation: validate evidence and freshness semantics, not exact
  Claude prose.
- Graph: ship the permission-filtered read model/API in the backend slice and
  render it later as a fixed-layout SVG.
- Incident fixture: runnable Python middleware and a focused pytest.
- UI proof: the new Slack graph node is the live-ingestion confirmation.
- Checkpoint cadence: normal 50 messages or 15 minutes; demo 3 messages or
  30 seconds; final flush at session end.
- Frontend: Next.js App Router, React, TypeScript, Tailwind CSS, and Motion for
  React in `apps/web`, using a same-origin BFF to FastAPI.
- Product surface: a Linear-inspired shell with Dashboard, Sources, and Task
  Context views.
- Dashboard proof: connector readiness and accepted evidence/indexing counts
  appear together.

## Workstream ownership

| Workstream | Exclusive responsibility | Shared integration boundary |
| --- | --- | --- |
| A — Corpus and adapters | Incident manifest, Python fixture, snapshot payloads, email adapter, provider normalization tests | Emits validated `RawEventInput` records |
| B — Retrieval and graph | Diversity reranking, golden evidence evaluator, graph contract/read model/API | Consumes canonical chunks and evidence packs |
| C — Runtime and acceptance | Compose services, Qdrant readiness, signed Slack transition, operator command, end-to-end tests | Owns the reproducible acceptance command |
| D — Frontend | `apps/web`, Dashboard, Sources, Task Context, graph, citation drawer, accessibility | Consumes allowlisted FastAPI contracts through the Next.js BFF |
| E — Assets and pitch | Deck, intro video, screenshots, captions, narration, run of show | Uses verified UI captures and redacted report counts |

No workstream may introduce a second retrieval implementation, let browser code
contact infrastructure directly, or claim a snapshot source is live.

## Finish line

The package is complete when:

- the operator command seeds and verifies the corpus idempotently;
- the first query returns the pre-incident state;
- a signed Slack event is normalized, embedded, indexed, and permissioned;
- the second query returns the new Slack evidence and a materially fresher
  evidence pack;
- the graph API contains the corresponding live Slack node;
- Claude Code can call the same task-context contract through MCP;
- the visual demo and public assets disclose every source mode correctly;
- two consecutive rehearsals complete in less than three minutes.
