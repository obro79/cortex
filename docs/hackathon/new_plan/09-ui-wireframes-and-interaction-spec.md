# 09 — UI wireframes and interaction specification

**Status:** Low-fidelity design contract
**Target:** Next.js shell at 1440×900, responsive to 375 px
**Views:** Dashboard, Sources, and `COR-123` Task Context

Numbers and timestamps drawn in the wireframes are illustrative layout
fixtures. Before capture, replace them with values from one accepted report ID;
no illustrative value may appear in a release artifact.

## Experience principles

1. **Evidence before spectacle.** Counts, timestamps, citations, and source mode
   are always legible.
2. **One reveal.** Live Slack arrival is the only dramatic motion.
3. **Dense but calm.** Linear-inspired hierarchy; no floating glass cards or
   decorative gradients.
4. **Task-scoped graph.** It explains a task rather than decorating a dashboard.
5. **Truth in every state.** Live, snapshot, simulator, stale, and failure are
   explicit text.

## Shared desktop shell

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ SIDEBAR 232       │ TOP BAR                                                  │
│                   │ Acme Engineering / Production       Demo truth  ⌘K   OF │
│ CORTEX            ├──────────────────────────────────────────────────────────┤
│                   │                                                          │
│ ● Overview        │ PAGE CONTENT                                             │
│ ○ Sources         │                                                          │
│ ○ Tasks           │                                                          │
│                   │                                                          │
│ MCP access        │                                                          │
│ Demo status       │                                                          │
│ Settings          │                                                          │
│                   │                                                          │
│ ───────────────   │                                                          │
│ 6 sources         │                                                          │
│ Slack: LIVE       │                                                          │
└───────────────────┴──────────────────────────────────────────────────────────┘
```

- Sidebar and top bar remain fixed; only main content scrolls.
- Active navigation uses blue text, stronger weight, and a 2 px indicator.
- `Demo truth` opens `Slack live · five demo snapshots`.
- `⌘K` is navigation/search, not an AI chat.
- Workspace identity and truth remain visible during the reveal.

## Wireframe A — Dashboard

Purpose: establish scale, readiness, and the active handoff opportunity within
15 seconds.

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ Overview                                            Updated 4 seconds ago    │
│ Always-current context for every agent              [Manage sources]         │
├──────────────────────────────────────────────────────────────────────────────┤
│ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────────────┐ │
│ │ 18           │ │ 42           │ │ 7            │ │ FRESH                │ │
│ │ indexed      │ │ searchable   │ │ queries      │ │ newest: Slack 4s ago │ │
│ │ events       │ │ chunks       │ │ this run     │ │ report demo_01H...   │ │
│ └──────────────┘ └──────────────┘ └──────────────┘ └──────────────────────┘ │
│                                                                              │
│ SOURCES                                                        6 configured │
│ ┌──────────────────────────────────────────────────────────────────────────┐ │
│ │ Slack LIVE ✓   GitHub SNAP ✓   Jira SNAP ✓   Email SNAP ✓               │ │
│ │ Drive SNAP ✓   Claude Code SNAP ✓                     [View all sources] │ │
│ └──────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│ ACTIVE CONTEXT                                                               │
│ ┌───────────────────────────────────────┬──────────────────────────────────┐ │
│ │ COR-123 · Session invalidation        │        GitHub      Jira          │ │
│ │ SEV-1 · Payments Platform             │           \        /             │ │
│ │                                       │ Claude ── COR-123 ── Slack       │ │
│ │ 6 sources · 1 conflict · fresh        │           /        \             │ │
│ │ Developer A left a safe checkpoint.   │        Email      Drive !        │ │
│ │                                       │                                  │ │
│ │ [Continue investigation →]            │  Task-scoped preview             │ │
│ └───────────────────────────────────────┴──────────────────────────────────┘ │
│                                                                              │
│ RECENT EVIDENCE ACTIVITY                     TASK CONTEXTS                    │
│ 12:04 Slack confirmation indexed             COR-123  Fresh  6 sources       │
│ 11:58 Claude checkpoint exported             PAY-88   Stale  3 sources       │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Dashboard behavior

- Metrics come from `DashboardSummary.reportId`.
- Hover/focus reveals definition and calculation timestamp.
- Source strip links to `/sources`; every item has a mode label.
- `Continue investigation` is the sole primary CTA.
- Preview graph is non-draggable and limited to seven nodes.
- Activity contains at most five safe events.
- Missing report replaces metrics with one error panel; never fake zeroes.

## Wireframe B — Sources

Purpose: show breadth, reveal prepared integrations, and prove evidence is
indexed/queryable.

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ Sources                                            [Reveal prepared sources] │
│ Connect your company's knowledge to every agent.                            │
│ Slack is live. Other providers use pre-indexed demo snapshots.              │
├─────────────────────────────────────────────────────────┬────────────────────┤
│ CONNECTORS                                              │ INDEXING PROOF     │
│ ┌──────────────────────┐ ┌──────────────────────┐      │ Accepted run       │
│ │ [Slack logo] Slack   │ │ [GitHub] GitHub      │      │ demo_01H...        │
│ │ LIVE                 │ │ DEMO SNAPSHOT        │      │                    │
│ │ 3 events · 4s ago    │ │ 4 events · 12m ago  │      │ 18 events          │
│ │ Incident channels    │ │ PRs and commits      │      │ 42 chunks          │
│ │ [Ready ✓]            │ │ [Connect]            │      │ 6 sources          │
│ └──────────────────────┘ └──────────────────────┘      │ 7 queries          │
│                                                        │                    │
│ ┌──────────────────────┐ ┌──────────────────────┐      │ Qdrant             │
│ │ [Jira] Jira          │ │ [Mail] Email         │      │ ● ready            │
│ │ DEMO SNAPSHOT        │ │ DEMO SNAPSHOT        │      │ collection: demo-v1│
│ │ 3 events             │ │ 2 events             │      │                    │
│ │ Tickets and owners   │ │ Customer impact      │      │ MODE LEGEND        │
│ │ [Connect]            │ │ [Connect]            │      │ ● Live             │
│ └──────────────────────┘ └──────────────────────┘      │ ◇ Demo snapshot    │
│                                                        │                    │
│ ┌──────────────────────┐ ┌──────────────────────┐      │ Connect reveals    │
│ │ [Drive] Drive/docs   │ │ [Claude] Claude Code │      │ prepared evidence; │
│ │ DEMO SNAPSHOT        │ │ DEMO SNAPSHOT        │      │ it does not OAuth  │
│ │ 3 events             │ │ 3 checkpoints        │      │ or ingest.         │
│ │ Plans and runbooks   │ │ Agent handoffs       │      │                    │
│ │ [Connect]            │ │ [Connect]            │      │ [View run report]  │
│ └──────────────────────┘ └──────────────────────┘      │                    │
└─────────────────────────────────────────────────────────┴────────────────────┘
```

### Source sequence

1. Initial state shows Slack `Ready`; snapshots show `Connect`.
2. Clicking `Connect` changes local state to `Presenting…`, then `Ready` after
   180 ms.
3. Its count crossfades into the proof panel under the same report ID.
4. `Reveal prepared sources` performs five transitions in reading order over
   about 2.5 seconds.
5. Ready cards expose `View evidence`, deep-linking to the task with a provider
   query parameter.
6. Session storage retains presentation state; backend counts remain canonical.

```text
UNREVEALED            PRESENTING             READY
[Connect]      →      [·· Presenting]   →     [✓ Ready]
snapshot badge        no network claim       View evidence
```

No card opens provider OAuth in the demo build.

## Wireframe C — Task Context before live arrival

Purpose: show agent-ready synthesis and provenance before the live update.

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ ← Tasks  COR-123 · Session invalidation after rollout        FRESH · 6 src  │
│ SEV-1  Payments Platform  Owner: Maya Chen       [Copy MCP prompt] [•••]     │
├──────────────────────────────────────────────────┬───────────────────────────┤
│ AGENT-READY CONTEXT                              │ EVIDENCE GRAPH            │
│                                                  │                           │
│ Current understanding                            │       GitHub      Jira     │
│ Session reads moved to Postgres, but an older    │          \        /        │
│ Redis fallback may still invalidate sessions.    │ Claude ─ COR-123          │
│                                                  │          /        \        │
│ Developer A checkpoint                           │       Email      Drive !   │
│ “Trace the fallback path and verify the rollout  │                           │
│ flag before changing code.”                      │  ○ supporting  ! conflict │
│                                                  │                           │
│ Recommended next actions                         │ WAITING FOR LIVE PROOF     │
│ 1. Inspect fallback flag in session middleware.  │ Checking Slack evidence…  │
│ 2. Compare PR config with stale runbook.          │ 00:31 remaining           │
│ 3. Confirm with live incident channel.           │                           │
│                                                  │ [Show evidence list]       │
│ 1 conflict · Drive guidance is older             │                           │
├──────────────────────────────────────────────────┴───────────────────────────┤
│ EVIDENCE TIMELINE                                                           │
│ 11:42 GitHub │ 11:45 Jira │ 11:51 Email │ 11:58 Claude │ Drive (older)     │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Pre-arrival behavior

- Task header stays visible while content scrolls.
- Context summary comes from backend evidence synthesis, never browser prose.
- Each next action has citation chips.
- Graph nodes, chips, and timeline items open the same drawer.
- The live window begins only after `Begin live proof` or `?live=1`; normal
  browsing does not poll forever.
- Timer text is not announced every second.

## Wireframe D — Live Slack arrival

```text
┌──────────────────────────────────────────────────┬───────────────────────────┐
│ AGENT-READY CONTEXT · UPDATED                    │ EVIDENCE GRAPH            │
│                                                  │                           │
│ New confirmation                                │       GitHub      Jira     │
│ Slack confirms the Redis fallback is active and │          \        /        │
│ invalidating sessions after the rollout.         │ Claude ─ COR-123 ─ SLACK   │
│                                                  │          /        \   LIVE │
│ Recommended next action changed                  │       Email      Drive !   │
│ Disable fallback behind the rollout flag, verify │                           │
│ session reads, then update the runbook.           │ ✓ Live evidence arrived   │
│                                                  │   12:04:19 · 2s ago        │
│ [Copy updated MCP prompt]                        │                           │
└──────────────────────────────────────────────────┴───────────────────────────┘
```

Arrival sequence:

1. Graph response contains Slack with `mode: live`.
2. `aria-live="polite"` announces arrival once.
3. Slack edge/node enter over 320 ms.
4. Gold outline pulses once, then settles.
5. Summary and next action crossfade to the new evidence pack.
6. Evidence-pack ID and timestamp visibly change.
7. Polling stops; duplicate nodes are impossible.

Reduced motion renders steps 3–5 immediately and retains text.

## Wireframe E — Citation drawer

```text
                                            ┌─────────────────────────────────┐
                                            │ SLACK                     [×]   │
                                            │ LIVE · Fresh · 12:04:19         │
                                            │                                 │
                                            │ #inc-customer-impact            │
                                            │ Redis fallback is still active  │
                                            │ and invalidating sessions after │
                                            │ the Postgres read rollout.      │
                                            │                                 │
                                            │ Supports                        │
                                            │ “Disable fallback behind flag.” │
                                            │                                 │
                                            │ Citation SLK-018                │
                                            │ Evidence pack evp_01H...        │
                                            │                                 │
                                            │ [Open evidence pack]            │
                                            └─────────────────────────────────┘
```

- 400 px desktop; full-height sheet below 768 px.
- Always show provider, mode, timestamp, freshness, approved excerpt,
  relationship, citation ID, and pack ID.
- Never show raw provider URL/payload.
- Escape closes and focus returns to the trigger.
- Drive drawer says `Conflicting evidence — older guidance` with text/icon.

## Responsive layouts

### Tablet, 768–1023 px

```text
┌──────┬──────────────────────────────────────────────┐
│ rail │ header                                       │
│ icons├──────────────────────────────────────────────┤
│ only │ summary / metrics                            │
│      │ graph                                        │
│      │ evidence list                                │
└──────┴──────────────────────────────────────────────┘
```

- Dashboard metrics become 2×2.
- Sources become two columns; proof moves above cards.
- Task summary stacks above graph; drawer overlays right.

### Mobile, 375 px

```text
┌──────────────────────────────┐
│ ☰  Cortex       Demo truth   │
├──────────────────────────────┤
│ COR-123 · FRESH              │
│ Session invalidation         │
│ [Copy MCP prompt]            │
│                              │
│ Agent-ready context          │
│ ...                          │
│ Evidence graph               │
│ [fit-to-width SVG]           │
│ Evidence timeline            │
│ [stacked rows]               │
└──────────────────────────────┘
```

- Summary, next action, graph, then evidence.
- Source cards use one column.
- Graph is a fixed semantic SVG, not a draggable canvas.
- No horizontal page scroll at 320 px or 200% zoom.
- Targets have at least 44×44 CSS px hit areas.

## Component map

```text
ProductLayout
├── SidebarNav
├── TopContextBar
├── DemoTruthPopover
└── PageSlot
    ├── DashboardPage
    │   ├── MetricGrid
    │   ├── SourceReadinessStrip
    │   ├── ActiveTaskCard
    │   ├── TaskGraphPreview
    │   └── EvidenceActivity
    ├── SourcesPage
    │   ├── SourceCardGrid
    │   ├── SourceCard
    │   ├── IndexingProofPanel
    │   └── SourceModeLegend
    └── TaskContextPage
        ├── TaskHeader
        ├── AgentContextPanel
        ├── TaskEvidenceGraph
        ├── LiveProofStatus
        ├── EvidenceTimeline
        └── CitationDrawer
```

Server Components own page shells and initial data. Client Components own the
navigation sheet, reveal state, command palette, graph selection, drawer, and
live polling.

## State matrix

| Surface | Loading | Empty/error | Success | Degraded |
| --- | --- | --- | --- | --- |
| Dashboard | geometry skeleton | report unavailable + retry | verified metrics | old report + timestamp |
| Sources | six card skeletons | manifest/report mismatch | six truthful cards | Qdrant unavailable |
| Task | summary/graph skeleton | task missing or graph retry | evidence context | safe stale graph |
| Live proof | explicit opt-in | transient retry | Slack arrival | 45-second timeout |
| Drawer | excerpt skeleton | citation unavailable | safe citation | redacted excerpt |

No state uses an unexplained spinner or blank panel.

## Keyboard and accessibility

- Skip link targets main content.
- Tab order follows sidebar → top bar → primary action → page sections.
- Graph nodes are real controls within semantic SVG groups.
- Arrow keys move between nodes; Enter/Space opens citation.
- Drawer has an accessible title and deterministic focus return.
- `aria-live` announces only arrival, timeout, and material errors.
- Status never relies on color.
- Graph has a text evidence-list alternative.

## Required captures

At 1440×900:

1. `dashboard-ready.png`
2. `sources-before.png`
3. `sources-ready.png`
4. `task-before-slack.png`
5. `task-slack-arrival.png`
6. `citation-slack.png`
7. `citation-conflict.png`
8. `task-mobile.png` at 375 px

Each capture includes source-mode disclosure or adjacent badges.

## Wireframe acceptance

- Every region maps to a named component.
- Every component has authoritative data, loading, error, and accessibility
  behavior.
- Dashboard → Sources → COR-123 has no dead end.
- Slack reveal is visually distinct, truthful, and recoverable.
- Design works without motion, hover, color perception, or a mouse.
- No view implies native Claude resume, unperformed OAuth, or a global company
  graph.
