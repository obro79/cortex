# Demo Assets, Slides, Video, and Pitch Plan

**Status:** Implementation-ready plan
**Owner:** Demo assets workstream
**Scope:** Presentation artifacts for the approved three-minute hybrid demo, including truthful recovery captures. This workstream does not change the application, backend, live Slack configuration, or credentials.

## Deliverable and narrative guardrails

Package a coherent story: Developer A creates a safe Claude Code checkpoint;
imported snapshots establish `COR-123`; a synthetic Slack message is delivered
live; Developer B uses Cortex in Claude Code before editing; the Next.js Task
Context view visibly receives fresh Slack evidence.

Every evidence artifact shows its source mode:

- **Live:** Slack only, and only after a verified live run.
- **Demo snapshot:** GitHub, Jira, Email, Drive/docs, and Claude Code checkpoint.
- **Fallback / prerecorded / signed-webhook simulator:** persistent, explicit frame label and matching narration.

Do not claim that Consume performs OAuth/indexing/ingestion; that Claude resumes, forks, or controls another native session; that non-Slack sources are live; or that recovery proof is live. Redact credentials, raw provider payloads, native session identifiers, raw transcripts, private URLs, and non-fixture windows.

## Asset manifest

| ID | Artifact | Required contents | Destination / format | Acceptance owner |
| --- | --- | --- | --- | --- |
| A01 | Intro master | 20-second source-convergence video, captions, audio mix | 1920×1080 MP4 + VTT/SRT + source timeline | media owner |
| A02 | Four-slide deck | four locked slides, notes, accessible PDF export | editable deck + 16:9 PDF | media owner |
| A03 | Frontend screenshots | ready, converged, live-arrival, and citation drawer states | PNG, 1920×1080 and docs variants | frontend/media |
| A04 | Claude Code hero capture | prepared request plus cited no-edit answer | 1920×1080 PNG/video segment | demo operator |
| A05 | Architecture/proof capture | safe sources → pipeline → permission-filtered MCP diagram | SVG/PNG + slide source | media owner |
| A06 | Recovery captures | prerecorded arrival and simulator result, clearly labelled | MP4/PNG separate from hero master | demo operator |
| A07 | Evidence/citation crops | Slack live, Claude snapshot, Drive/docs conflict | PNG with visible badge/timestamp/freshness | media owner |
| A08 | Pitch package | 60-second pitch, one-page pitch, final demo script | Markdown/PDF + presenter notes | pitch owner |
| A09 | Rehearsal record | two timed logs, source-mode checklist, asset hashes | Markdown/JSON with artifacts | central integration |

Use IDs in filenames. The manifest records capture date, commit, run/evidence-pack ID, source mode, redaction review, and checksum. Keep raw recordings and editable files separate from final judge-facing exports.

## Four-slide deck

The deck is sparse: one claim per slide, large type, already-landed Cortex palette, and no generic connector-dashboard imagery. Slides are used at 0:20–0:35, 2:35–2:50, and only as a static recovery bridge; they never replace live proof.

### Slide 1 — thesis (0:20–0:35)

**Headline:** `Always-current context for every agent.`
**Support:** `A trustworthy handoff combines what the prior agent established with what changed moments ago.`

Visual: `COR-123` centred, muted snapshot source marks, one gold Slack mark. Footer: `Slack live in this demo • other sources are demo snapshots`.

Speaker line: “The handoff should not depend on a transcript or a human remembering to summarize: Cortex gives every agent current, inspectable context.”

### Slide 2 — problem and convergence (0:35–0:45)

**Headline:** `The handoff broke because the evidence changed.`
**Support:** `Developer A had a safe checkpoint. A newer Slack update changed the diagnosis.`

Visual: six labelled sources converge into `COR-123`; Drive/docs has bronze `conflicting`, Slack has gold `Live`, other labels have `Demo snapshot`. Do not animate in a way that resembles connection setup.

Speaker line: “Search across sources is not enough. The next agent needs the prior decision, contradictory document, and freshest signal together.”

### Slide 3 — proof architecture (2:35–2:50)

**Headline:** `One safe evidence path, exposed through MCP.`
**Support:** `Snapshots and live Slack normalize into permission-filtered task context; Claude asks before it edits.`

Visual: Sources → canonical event pipeline → Postgres/Qdrant → permission-filtered `get_task_context` → Claude Code / evidence graph. Label Slack `Live synthetic demo channel`, all other inputs `Imported demo snapshots`, and a callout `safe metadata, citations, freshness`.

Speaker line: “The source details stay inspectable; the agent receives context and citations, not a hidden opaque answer.”

### Slide 4 — close (2:50–3:00)

**Headline:** `One context layer. Every agent. No manual handoff.`
**Support:** `Current evidence, visible provenance, and a safe next action.`

Visual: minimal final graph with gold Slack, bronze stale doc, distinct Claude checkpoint. Repeat source-mode footer.

Speaker line: “Cortex lets the next agent start from what is known now, show why, and ask before changing anything.”

Deck accessibility: 16:9 1920×1080 master; minimum 28 pt body and 44 pt headline; AA contrast in light/dark projected variants; reading-order-checked PDF; alt text for non-decorative diagrams; and notes containing visual meaning. Never encode source mode, Live, or conflict by color alone.

## Twenty-second source-convergence intro

Play this video from 0:00–0:20 before Slide 1. Deliver captions burned into the review cut and as VTT/SRT. Narration leaves room for the live run.

| Time | Picture / motion | On-screen copy | Narration / sound |
| --- | --- | --- | --- |
| 0–3s | Cortex title resolves; quiet COR-123 marker appears. | `Always-current context for every agent` | “Every agent should begin with what the team knows now.” |
| 3–8s | Six cards converge; five settle snapshot, Slack visibly Live. | `Slack live • five demo snapshots` | “Cortex brings incident evidence together, without pretending every source is live.” |
| 8–13s | Claude Code work becomes a bounded approved checkpoint; no transcript UI. | `Developer A: approved checkpoint • Demo snapshot` | “Developer A leaves a safe checkpoint: suspected fallback, test, and next question.” |
| 13–17s | Fixed COR-123 graph forms; Drive/docs gets bronze conflict treatment. | `Stale rollout guidance conflicts` | “The graph keeps support, conflict, and freshness visible.” |
| 17–20s | Developer B terminal receives context/citation preview; end card lands. | `Pick up COR-123 with current evidence` | “When Slack changes, the next agent sees it before making a change.” |

Motion is 200–400 ms per element, no rapid flashing. Produce a reduced-motion cut using crossfades only and an audio-only transcript. Any music stays under narration and is licensed/attributed in the manifest.

## Three-minute hybrid shot list

| Time | Operator picture | Spoken proof | Required visible state |
| --- | --- | --- | --- |
| 0:00–0:20 | Play A01 intro. | Video narration. | Source-mode disclosure; no raw transcript. |
| 0:20–0:35 | Slide 1. | Thesis and live/snapshot boundary. | Footer: Slack live; five snapshots. |
| 0:35–0:45 | `/sources`, reveal the six prepared cards. | “These cards reveal evidence prepared before the run.” | Six badges; no syncing/OAuth claim; completes ~3s. |
| 0:45–1:05 | Real synthetic Slack channel and prepared message. | “This is the one live source.” | Synthetic channel only; no tokens/private context. |
| 1:05–1:20 | Open `/tasks/COR-123`. | “That new Slack evidence is arriving now.” | Polling status then gold Live node/edge. |
| 1:20–2:15 | Claude Code request/response. | “Use Cortex before changing anything.” | Prepared request; citations/freshness; no edit command. |
| 2:15–2:35 | Open Slack, Claude, Drive/docs drawers. | “New, prior, and conflicting evidence are inspectable.” | Badges, timestamps, excerpts, evidence-pack action. |
| 2:35–2:50 | Slide 3. | Architecture/proof explanation. | Correct source labels. |
| 2:50–3:00 | Slide 4. | Closing line. | `One context layer. Every agent. No manual handoff.` |

The Claude Code capture shows this exact request:

> Pick up the COR-123 session incident. Use Cortex before changing anything. Tell me what Developer A established, what changed since then, the likely cause, conflicting evidence, and the safest next file and test to inspect.

The answer cites all six sources, distinguishes the prior checkpoint from newer Slack, names stale Redis documentation conflict/customer impact/likely fallback cause, names exact fixture middleware file and focused test, and requests approval before editing. If output drifts, use a labelled captured MCP exchange with the same evidence-pack ID; do not present it as live.

## Recovery captures

Capture before final rehearsal but do not mix into the hero video:

1. **Slack-node arrival replay:** 10–15 seconds waiting graph to gold Slack node. Persistent banner: `PRERECORDED RECOVERY — captured from a verified live Slack run on [date/run ID]`.
2. **Signed-webhook simulator:** separate capture with control and graph outcome. Persistent banner: `SIMULATED FALLBACK — signed webhook simulator, not live Slack`.
3. **Claude answer fallback:** captured MCP exchange with exact evidence-pack ID and banner: `PRERECORDED RECOVERY — captured response`.

Recovery narration says what failed and which labelled capture is used. Never crop away banner, splice recovery into live segment, or claim its timing proves the service.

## Pitch package

### 60-second spoken pitch

“Every agent inherits a moving target. The previous agent may have found the right file, but a Slack update, a stale rollout document, and a support escalation can change what is safe to do next. Cortex is the evidence-first context layer for that handoff.

In this demo, Developer A leaves an approved structured checkpoint for COR-123. Cortex combines it with imported GitHub, Jira, email, and Drive snapshots, and with one live synthetic Slack update. The task graph shows not only the answer, but what is fresh and what conflicts. Developer B asks Claude Code for context before editing; it cites evidence, names the safest file and test, and asks for approval.

We are not claiming a live connector suite: Slack is the only live source here. The point is trustworthy continuity—one context layer, every agent, no manual handoff.”

### One-page pitch structure

1. Thesis and incident opening.
2. Problem: handoffs lose evidence and freshness.
3. Product: canonical, permission-filtered, cited task context through MCP.
4. Proof: snapshot corpus plus sole live Slack update and graph arrival.
5. Trust boundary: source modes, approved checkpoints, no transcript/session resumption, no unlabelled fallback.
6. Closing: `One context layer. Every agent. No manual handoff.`

## Production and validation checklist

- Capture only after operator preflight and verified graph/citation run; record commit SHA, evidence-pack ID, modes, and timestamp.
- Review every frame at 100% for credentials, tokens, real names, private URLs, raw messages/transcripts, and session handles. Re-capture rather than rely on unreadable blur.
- Confirm source badges/fallback banners survive export, crop, PDF conversion, and projected contrast.
- Validate captions, slide reading order/alt text, audio levels, and 1920×1080 playback.
- Verify screenshots cover ready, all-consumed, live arrival, Slack drawer, Claude drawer, Drive/docs conflict drawer, and each recovery mode.
- Run two complete rehearsals under 3:00, including recovery path; record timings and interventions.
- Final acceptance: live Slack node appears within 10 seconds of webhook receipt in the verified run; every public asset communicates source boundary; no recovery capture is mistaken for live proof.

## Bounded tickets

1. Create deck master, four locked slides, notes, accessible PDF, and style checks using Cortex palette tokens.
2. Produce/caption intro plus reduced-motion/audio-transcript variants from approved timeline.
3. Capture/redact frontend, Claude, architecture, and citation set; populate A03–A07 manifest.
4. Record, label, and store three recovery captures separately.
5. Write/export 60-second and one-page pitch, stage script, and source-mode disclosure checklist.
6. Run asset review and two timed rehearsals; freeze exports only after central live-run verification.

## Dependencies and risks

Capture depends on the final snapshot corpus, safe citation/evidence-pack data,
the three Next.js product views, graph endpoint, and credentialed synthetic
Slack acceptance run. The only substitute for unavailable live Slack is an
explicitly labelled recovery capture. Exact middleware-file and focused-test
names come from the final incident fixture and must be copied verbatim into the
Claude capture—not invented by the asset workstream.
