# Presentation Frontend Plan — `/ui/demo`

**Status:** Implementation-ready plan
**Owner:** Presentation frontend workstream
**Scope:** A dedicated, truthful three-minute-demo surface; no changes to existing diagnostic screens.

## Outcome and truth boundary

Deliver `/ui/demo`, a polished incident presentation for `COR-123`. It makes the six already-indexed source contributions legible, then proves freshness by adding the sole live source (Slack) to a task-scoped graph.

- Slack is the only live provider. Its card and graph node are labelled `Live`.
- GitHub, Jira, Email, Drive/docs, and Claude Code are imported evidence and are labelled `Demo snapshot`.
- Clicking `Consume` changes only local presentation state for evidence that the operator preparation step already indexed. It must never start OAuth, backfill, indexing, or an ingestion request, and the UI copy must say so.
- The graph is a bounded task evidence projection, not a company knowledge graph. No global graph, ingestion ticker, general chat, or connector administration belongs in this route.
- Browser responses and rendered content contain safe graph metadata and approved excerpts only—never provider tokens, raw provider payloads, transcripts, private source URLs, native session handles, or vector payloads.

## Interface assumptions

The browser BFF exposes only the read-only graph contract:

```text
GET /v1/demo/tasks/COR-123/graph

TaskEvidenceGraph {
  task_ref, generated_at,
  nodes: [{
    id, kind: "task" | "evidence", provider, label,
    mode: "live" | "imported_snapshot" | "fixture",
    freshness, source_updated_at, citation_id?
  }],
  edges: [{ id, source, target, relationship,
            state: "supporting" | "conflicting" }]
}
```

The frontend treats a graph response as authoritative for node mode, freshness, timestamps, and conflict state. Citation drawer details are fetched or resolved through the existing safe evidence-pack/citation interface keyed by `citation_id`; it does not construct provider URLs. The planned six source identifiers and expected labels are: `slack`, `github`, `jira`, `email`, `drive_docs`, and `claude_code`.

The page needs a stable snapshot graph before live proof begins. If the API already includes Slack after a rehearsal, render it as an already-present `Live` node and skip the arrival animation, while retaining truthful badge and citation information.

## Exact screen states

### 1. Ready / source convergence

At route entry, show:

- A persistent title: `Cortex — Always-current context`.
- A one-line disclosure: `Slack is live in this run. Other sources are pre-indexed demo snapshots.`
- Six connector cards in this fixed reading order: Slack, GitHub, Jira, Email, Drive/docs, Claude Code.
- Per-card provider icon plus visible textual provider name, a mode badge, a concise role line, and a `Consume` button.
- The graph panel in its pre-live state, with `COR-123` at centre and snapshot evidence visible once consumed.

Cards begin unconsumed. The Slack card reads `Live` but its Consume action remains presentation-only: it connects the already-known card to the incident and does not claim a Slack fetch. The graph has no Slack evidence node until the live endpoint returns one.

| Card | Badge | Role copy |
| --- | --- | --- |
| Slack | Live | `Newest confirmation: Redis fallback invalidates sessions.` |
| GitHub | Demo snapshot | `Rollout changed session reads to Postgres.` |
| Jira | Demo snapshot | `COR-123 records severity, version, and owner.` |
| Email | Demo snapshot | `Support escalation establishes customer impact.` |
| Drive/docs | Demo snapshot | `Older rollout guidance still permits Redis fallback.` |
| Claude Code | Demo snapshot | `Developer A checkpoint: suspected fallback path and next action.` |

Below the cards, include non-actionable explanatory text: `Consume reveals evidence prepared before this presentation; it does not connect or ingest a provider.`

### 2. Consuming snapshots

Each click consumes exactly one card, disables its button, changes its label to `Connected to COR-123`, and exposes that source's fixed graph node/edge. The auto-demo control consumes cards in the listed order; it is optional and keyboard-accessible. The run completes in approximately three seconds (roughly 450 ms between starts, with short overlapping settle animations).

The card transition is a 180–240 ms border/accent settle and a short line-draw toward the graph panel. Do not use spinner, network, OAuth, download, or “syncing” language. Graph nodes fade from 0 to 1 and supporting edges draw once; their final state remains still.

### 3. Awaiting live proof

After the snapshot sequence, show: `Waiting for the prepared Slack update…` and `Checking task evidence every second (up to 45 seconds).` Begin polling only in this live-window state. Poll once per second, preventing overlapping requests. Stop on the first response that includes evidence where provider is `slack` and mode is `live`, or after 45 seconds. Cancel the timer on unmount, route change, and successful arrival. Preserve the last safe graph on transient errors.

At timeout show: `No live Slack update arrived in this window.` with the operator-only recovery cue: `Use the labelled prerecorded arrival capture or signed-webhook-simulator fallback.` Never silently insert a live node.

### 4. Live node arrival

On the response that first adds live Slack, announce: `Live Slack evidence arrived for COR-123.` Update status to `Fresh Slack confirmation received`. The Slack node and edge fade in over 300–400 ms, then pulse its gold/fresh outline once (about 700 ms) and settle. With reduced motion, render it immediately with no fade, movement, or pulse while retaining the textual announcement.

### 5. Citation drawer

Selecting a graph node opens a compact drawer without navigation. It contains, in order: provider and source label, `Live` or `Demo snapshot` badge, source timestamp, freshness label, approved excerpt, and `Open evidence pack`. The stale Drive/docs node also says `Conflicting evidence — older guidance`.

The drawer has an accessible name built from the selected source, traps focus while modal on narrow screens, returns focus to its node on close, supports Escape, and never displays a raw source link.

## Fixed-layout SVG graph

Use a dependency-free semantic SVG—no graph package or runtime force simulation. The viewBox, node positions, and edge paths are fixed:

```text
                       GitHub        Jira
                          \          /
      Claude Code -------- COR-123 -------- Slack (gold, fresh; arrives live)
                          /          \
                       Email     Drive/docs (bronze, conflicting)
```

- `COR-123` is the large central task node.
- Snapshot supporting edges use existing Cortex neutral/semantic palette tokens.
- Slack uses the landed gold/fresh treatment only after a `mode: live` response.
- Drive/docs uses bronze/conflict treatment and a visible conflict indicator; color is never the only signal.
- Claude Code has a visually distinct agent-session treatment plus textual label.
- Every node is a real focusable control with an accessible label containing provider, mode, and freshness. Tab/Shift+Tab selects nodes; Enter/Space opens the drawer.
- Edges are non-interactive decorations; accessible reading order matches card order, then task, then graph evidence nodes.

Desktop uses a stable two-column composition: cards/status left and a large graph right, with drawer adjacent to or overlaying graph. Below 900 px stack cards, status, graph, then drawer; retain the fixed SVG viewBox and avoid label text smaller than readable size. At 200% zoom and 320 CSS px, all actions and disclosure remain available without two-dimensional page scroll for ordinary reading.

## Visual and accessibility requirements

- Reuse landed Cortex light/dark tokens, semantic warning colors, and existing button/card conventions; do not invent a second palette.
- Maintain WCAG AA contrast for text, node labels, badges, focus states, and gold/bronze treatments in both themes.
- Give the page one H1, logical H2s for Sources and Task evidence, and an `aria-live="polite"` region for arrival/timeout only. Do not announce every poll.
- Provider icons are decorative when adjacent text is visible; otherwise name them. Respect `prefers-reduced-motion`.
- All cards, nodes, evidence-pack links, and close controls work by keyboard with clear focus. Do not use hover-only content.

## Bounded implementation tickets

1. **Demo route shell and disclosure:** add `/ui/demo`, source card data, exact labels/badges, theme-consistent layout, and static status regions.
2. **Connector convergence state:** implement local Consume/auto-demo state, three-second sequence, truthful copy, and reduced-motion path.
3. **Task graph component:** implement fixed SVG layout, safe graph projection, supporting/conflicting/fresh/agent treatments, and responsive behavior.
4. **Live Slack polling:** add one-second non-overlapping polls, 45-second ceiling, lifecycle cleanup, arrival/timeout/error states, and arrival motion.
5. **Citation drawer:** add safe citation display, focus management, keyboard controls, and evidence-pack action.
6. **Frontend verification:** add focused component/integration tests and browser captures for the cases below.

## Validation and acceptance

Automated checks:

- Unit-test card labels, mode badges, and Consume actions to ensure no browser ingestion/OAuth request is issued.
- Test full card sequence completes in <=3 seconds and reduced motion renders final states without timing dependence.
- Test polling starts only in the live window, runs once per second without overlap, stops on a live Slack node or exactly at 45 seconds, and cleans up on unmount.
- Test a transient poll failure preserves the current graph and timeout never creates Slack evidence.
- Test arrival adds node/edge once, announces correctly, and skips arrival animation if Slack existed at initial load.
- Test conflict and agent-session semantics are not color-only, plus drawer content/focus/Escape and keyboard graph selection.
- Run repository lint, typecheck, production build, and browser checks at desktop and 320 px/reduced-motion viewports.

Acceptance is met when a presenter can load `/ui/demo`, consume all six pre-indexed cards in approximately three seconds, wait for a real Slack-backed graph response, see its gold node within ten seconds of webhook receipt, and inspect Slack, Claude Code, and stale Drive/docs provenance. The screen always discloses source modes and never implies interactive provider connection or hides a live failure behind simulation.
