# 08 — Ambiguity register and decision ledger

**Status:** Active control document
**Purpose:** Expose assumptions before they create rework
**Rule:** Proceed on a documented default unless its row is `BLOCKING`

## Status meanings

- `LOCKED`: implementation follows this decision.
- `DEFAULTED`: proceed unless new evidence invalidates the default.
- `BLOCKING`: stop at the named boundary until the artifact exists.
- `EXTERNAL`: credentials/provider state are needed for final proof, but local
  work continues against contracts and simulators.

## Product and demo

| ID | Status | Ambiguity | Decision/default | Verification |
| --- | --- | --- | --- | --- |
| P-01 | LOCKED | Is Cortex a new chat agent? | No. It is MCP-accessible context infrastructure for existing agents. | UI has no general chat composer. |
| P-02 | LOCKED | What is the hero? | Developer B continues `COR-123` using cross-source evidence and Developer A's safe checkpoint. | Golden MCP exchange. |
| P-03 | LOCKED | Which provider is live? | Slack only; five others are `Demo snapshot`. | UI/video/deck badges. |
| P-04 | LOCKED | What does `Connect` mean? | Presentation reveal, never OAuth or ingestion. | Browser network assertion. |
| P-05 | LOCKED | What scale can be claimed? | Only counts in an accepted report ID. | Dashboard and asset manifest. |
| P-06 | DEFAULTED | Is the wow moment the graph? | Agent continuation is the outcome; graph arrival is visible proof. | Run-of-show timing. |

## Corpus and ingestion

| ID | Status | Ambiguity | Decision/default | Verification |
| --- | --- | --- | --- | --- |
| B-01 | BLOCKING | What are the exact 18 records? | Freeze stable IDs, timestamps, modes, decisive/distractor roles, task refs, and expected citations. | Manifest checksum. |
| B-02 | LOCKED | May fixtures insert into SQL? | No; all use `RawEventInput` and the shared pipeline. | Lineage test. |
| B-03 | DEFAULTED | How is the live transition counted? | Preparation yields 17 records; signed Slack yields the decisive 18th. | Pre/post reports. |
| B-04 | DEFAULTED | How is `COR-123` attached? | Explicit fixture metadata plus normal entity extraction. | Normalization assertion. |
| B-05 | DEFAULTED | Which timestamps? | Fixed UTC times relative to a frozen demo epoch. | Repeatable seed test. |
| B-06 | DEFAULTED | What is email? | Generic normalized snapshot, not a live Gmail/Outlook claim. | Adapter fixture. |
| B-07 | BLOCKING | What may be public? | Only synthetic/redacted manifest content. | Asset redaction review. |

## Checkpoint and MCP

| ID | Status | Ambiguity | Decision/default | Verification |
| --- | --- | --- | --- | --- |
| A-01 | LOCKED | Are native Claude sessions ingested? | No; a local exporter creates an explicit safe envelope. | Contract rejection tests. |
| A-02 | DEFAULTED | How is export triggered? | Explicit CLI plus optional session-end hook; no scraping. | CLI integration test. |
| A-03 | LOCKED | What is identity? | `checkpoint_id + content_hash` using existing agent-session event identity. | Idempotency test. |
| A-04 | DEFAULTED | What is exported? | Goal, completed work, decisions, blockers, next actions, file/task refs, bounded summary. | Schema/redaction test. |
| A-05 | BLOCKING | Which MCP tool is demoed? | Default `get_task_context`; freeze tool name and JSON before recording. | Golden exchange fixture. |
| A-06 | DEFAULTED | Can UI say `Open in Claude Code`? | Only setup/copy instructions, not native session control. | Copy review. |
| A-07 | DEFAULTED | Evidence-pack size? | Summary, at most six decisive citations, conflicts, freshness, and next actions. | Size assertion. |

## Retrieval, Qdrant, and graph

| ID | Status | Ambiguity | Decision/default | Verification |
| --- | --- | --- | --- | --- |
| R-01 | LOCKED | Is Qdrant local and hosted? | One adapter/collection contract; Compose first, hosted parity second. | Parity matrix. |
| R-02 | EXTERNAL | Which hosted cluster? | Environment variables only; Compose until credentials arrive. | Hosted smoke report. |
| R-03 | DEFAULTED | Which embedding profile? | Pin existing production profile; deterministic embeddings are test-only. | Collection metadata. |
| R-04 | LOCKED | Does diversity replace relevance? | No; bounded post-fusion coverage boost retaining original scores/reasons. | Ranking provenance test. |
| R-05 | DEFAULTED | Where does coverage apply? | Recognized task/entity retrieval only; generic search unchanged. | Regression queries. |
| R-06 | DEFAULTED | Is graph global? | No; permission-filtered projection for one task. | Authenticated task API. |
| R-07 | DEFAULTED | Graph size? | One task, at most 18 evidence nodes and 30 edges. | Response-size test. |
| R-08 | DEFAULTED | How are conflicts shown? | Edge state, reason, and older timestamp; not color alone. | Drive conflict fixture. |
| R-09 | BLOCKING | What makes post-update fresher? | New Slack citation, newest timestamp, and changed next action. | Golden evaluator. |

## Slack and runtime

| ID | Status | Ambiguity | Decision/default | Verification |
| --- | --- | --- | --- | --- |
| S-01 | LOCKED | Is a simulator allowed? | Yes when labelled; final preferred path uses real Slack. | Run report mode. |
| S-02 | EXTERNAL | Are final credentials available? | Unknown; simulator unblocks code/tests. | Preflight. |
| S-03 | LOCKED | How is simulator authenticity protected? | Same signed webhook and mapping path as real Slack. | Signature/replay tests. |
| S-04 | DEFAULTED | What if Slack is already indexed? | Reset only isolated demo workspace via idempotent preparation. | Two-run rehearsal. |
| S-05 | DEFAULTED | Polling window? | One non-overlapping poll/second, maximum 45 seconds. | Browser timer test. |
| S-06 | DEFAULTED | Startup contract? | One Compose command plus one idempotent preparation command. | Fresh-clone run. |
| S-07 | BLOCKING | Can assets claim hosted Qdrant? | Only after hosted smoke evidence; otherwise label Compose. | Truth review. |

## Frontend

| ID | Status | Ambiguity | Decision/default | Verification |
| --- | --- | --- | --- | --- |
| F-01 | LOCKED | Frontend stack? | Next.js App Router, React, TypeScript, Tailwind, Motion. | `apps/web` build. |
| F-02 | LOCKED | Repository topology? | Same repository, separate `apps/web` service. | Compose topology. |
| F-03 | LOCKED | Browser/backend boundary? | Same-origin Next.js BFF with allowlisted FastAPI routes. | Network audit. |
| F-04 | LOCKED | Product views? | Dashboard, Sources, Task Context. | Route tests. |
| F-05 | LOCKED | Dashboard purpose? | Both connector readiness and accepted evidence/indexing scale. | Wireframe assertions. |
| F-06 | DEFAULTED | Navigation? | Linear-inspired sidebar; mobile sheet below 768 px. | Responsive captures. |
| F-07 | LOCKED | Global animated graph? | No; bounded dashboard preview and full task projection. | Component inventory. |
| F-08 | DEFAULTED | Is reveal state persistent? | Session storage only; backend remains authoritative. | Reload test. |
| F-09 | DEFAULTED | Animation package? | Current `motion` package imported from `motion/react`. | Dependency test. |
| F-10 | DEFAULTED | Primary viewport? | 1440×900, responsive to 375 px. | Capture matrix. |

## Assets and pitch

| ID | Status | Ambiguity | Decision/default | Verification |
| --- | --- | --- | --- | --- |
| D-01 | LOCKED | Are screenshots generated? | Product shots come from accepted run; generated art is decorative only. | Manifest. |
| D-02 | DEFAULTED | Slide count? | Four core slides plus hidden recovery appendix. | Deck checklist. |
| D-03 | DEFAULTED | What is prerecorded? | 20-second opener and labelled recovery clips only. | Captions/slates. |
| D-04 | BLOCKING | Which counts enter pitch? | Freeze after accepted report; placeholders cannot ship. | Deck lint. |
| D-05 | DEFAULTED | Visual language? | Same tokens, typography, graph shapes, and badges as product. | Visual review. |

## Remaining user/external gates

Only these may need input before final release:

1. Final Slack workspace/app credentials and channel.
2. Hosted Qdrant endpoint/key and whether to make the hosted claim.
3. Final public product name/domain if not Cortex.
4. Availability of a safe Claude Code launcher; default is copyable MCP setup.
5. Final accepted counts for screenshots, deck, pitch, and video.

Everything else has a safe default and should proceed without waiting.

## Resolution cadence

- Review `BLOCKING` rows before implementation each day.
- Update a row in the same commit that resolves its contract.
- Never change `LOCKED` silently; add an ADR note and update tests.
- At release freeze, no `BLOCKING` row remains and each `EXTERNAL` row is
  truthfully labelled.
