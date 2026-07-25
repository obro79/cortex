# 04 — Next.js presentation frontend plan

**Status:** Decision-complete architecture; implementation-ready after backend
contract fixtures land
**Owner:** Presentation frontend workstream
**Scope:** A polished three-view Cortex product shell for the hackathon demo

## Outcome and truth boundary

Build a frontend application in `apps/web` using Next.js App Router, React,
TypeScript, Tailwind CSS, and Motion for React. FastAPI remains the system of
record for ingestion, retrieval, graphs, evidence, and MCP behavior. Next.js
owns presentation and acts as the browser-facing BFF.

The product has three primary views:

1. `/dashboard` — connector readiness and evidence-scale control room.
2. `/sources` — source marketplace, source mode, and indexing proof.
3. `/tasks/COR-123` — incident context, task graph, citations, and live Slack
   arrival.

Truth rules are global:

- Slack is the only live provider in the final acceptance run.
- GitHub, Jira, Email, Drive/docs, and the initial Claude Code checkpoint are
  visibly labelled `Demo snapshot`.
- `Connect` and `Consume` reveal prepared demo evidence. They never claim to
  perform OAuth or indexing.
- Counts come from an accepted demo report or an explicitly labelled fixture
  response; components never invent them.
- Browser responses contain no provider tokens, raw payloads, transcripts,
  private source URLs, native session handles, or vector payloads.

## Repository and runtime topology

```text
cortex/
├── apps/
│   └── web/
│       ├── app/
│       │   ├── (product)/layout.tsx
│       │   ├── (product)/dashboard/page.tsx
│       │   ├── (product)/sources/page.tsx
│       │   ├── (product)/tasks/[taskRef]/page.tsx
│       │   └── api/cortex/[...path]/route.ts
│       ├── components/{shell,dashboard,sources,task-context}/
│       ├── lib/{cortex-api,contracts,demo-state,motion}.ts
│       └── public/providers/
├── src/cortex/                 # existing FastAPI backend
└── docker-compose.yml          # adds web service and health dependency
```

- The browser calls only same-origin `/api/cortex/*`.
- The Next.js route handler forwards an allowlisted set of read/demo requests
  to FastAPI using `CORTEX_API_INTERNAL_URL`.
- Browser-supplied workspace or actor headers are ignored. The BFF derives demo
  identity from server configuration or an authenticated session.
- Simulator mutations do not pass through a generic wildcard. A narrow demo
  action gets its own route, method, CSRF check, and allowlist.
- Existing FastAPI `/ui` screens remain available for internal diagnostics but
  are not part of the presentation product.
- Compose publishes the frontend on `http://localhost:3000` and keeps FastAPI
  on the internal network plus its diagnostic port.

Official implementation references:

- [Next.js App Router](https://nextjs.org/docs/app)
- [Next.js rewrites](https://nextjs.org/docs/app/api-reference/config/next-config-js/rewrites)
- [Tailwind CSS with Next.js](https://tailwindcss.com/docs/installation/framework-guides/nextjs)
- [Motion for React](https://motion.dev/docs/react)
- [Reduced motion](https://motion.dev/docs/react-use-reduced-motion)

## Data-fetching boundary

Server Components fetch stable initial data:

- workspace identity and demo disclosure;
- source summaries and verified counts;
- recent task contexts;
- initial `TaskEvidenceGraph`;
- initial evidence pack for `COR-123`.

Client Components own interaction only:

- connector-card presentation state;
- command palette and responsive navigation;
- graph node selection;
- citation drawer focus management;
- bounded live-Slack polling;
- Motion transitions.

No client component imports an internal FastAPI URL. Typed functions in
`lib/cortex-api.ts` validate runtime responses before rendering.

```ts
type SourceMode = "live" | "demo_snapshot" | "fixture";

type DashboardSummary = {
  reportId: string;
  generatedAt: string;
  indexedEvents: number;
  indexedChunks: number;
  queryCount: number;
  sourceCount: number;
  liveSourceCount: number;
  freshness: "fresh" | "degraded" | "stale";
  sources: SourceSummary[];
  recentTasks: TaskSummary[];
};

type SourceSummary = {
  provider:
    | "slack"
    | "github"
    | "jira"
    | "email"
    | "google_drive"
    | "agent_session";
  displayName: string;
  mode: SourceMode;
  status: "ready" | "presenting" | "waiting_live" | "error";
  indexedEvents: number;
  lastIndexedAt: string | null;
  disclosure: string;
};
```

Python schemas are canonical. TypeScript contracts are generated from or tested
against backend OpenAPI/JSON fixtures; they may not drift silently.
Visual identity is a separate, explicit mapping: `email` uses the Gmail mark
only for a Gmail connection, `agent_session` uses the Anthropic mark without
claiming it is an official Claude Code logo, and the connector-family Atlassian
asset is not a seventh indexed source.

## Product shell

Use a dense, restrained, Linear-inspired shell:

- 232 px persistent left navigation above 1024 px.
- 64 px rail from 768–1023 px; mobile sheet below 768 px.
- 48 px top context bar with workspace, `⌘K`, environment, and demo disclosure.
- Main content uses a 12-column grid, 24 px gutters, and 1540 px maximum width.
- One primary action per view.

```text
Cortex
Overview
Sources
Tasks
────────
MCP access
Demo status
Settings
```

Only Overview, Sources, and `COR-123` need complete demo behavior. Other items
may be visibly disabled with `After hackathon`; they must not lead to dead
screens.

## View responsibilities

### `/dashboard`

Combine connector readiness and evidence proof:

- verified metric cards for events, chunks, queries, and freshness;
- compact six-provider readiness strip;
- dominant `Continue COR-123` card with evidence coverage;
- bounded task-context graph preview;
- recent safe evidence activity;
- secondary `Manage sources` action.

The preview is a task projection, not a global Obsidian graph.

### `/sources`

Show six fixed provider cards and an `Indexing proof` panel:

- official icon and text name;
- `Live` or `Demo snapshot` badge;
- indexed-event count and last-indexed timestamp;
- evidence role;
- `Connect`/`Ready` presentation state;
- `View evidence` deep link.

The proof panel shows accepted-run counts, report ID, Qdrant status, and source
truth. `Connect` animates prepared evidence into the panel without invoking
provider OAuth.

### `/tasks/COR-123`

The hero view contains:

- incident header and freshness;
- agent-ready context summary;
- fixed-layout evidence graph;
- evidence timeline;
- live Slack waiting/arrival state;
- citation drawer;
- `Copy MCP prompt` and Claude Code setup instructions, without claiming native
  session control.

## Motion system

Use the current `motion` package imported from `motion/react`.

| Interaction | Motion | Duration | Reduced motion |
| --- | --- | --- | --- |
| Route content | opacity + 4 px settle | 160 ms | opacity only, 80 ms |
| Source reveal | border/color + opacity | 180 ms | instant |
| Metric update | number crossfade | 180 ms | replace |
| Graph arrival | opacity + scale 0.96→1 | 320 ms | immediate |
| Slack proof | one outline pulse | 700 ms | text only |
| Drawer | opacity + x 12→0 | 180 ms | opacity only |

Do not animate layout dimensions, run ambient graph motion, add parallax, or
loop a pulse. Motion communicates cause and effect only. Use
`useReducedMotion()` and preserve equivalent text.

## Visual system

```text
navy        #2B4162  navigation and strong text
blue        #385F71  links, selection, supporting evidence
off-white   #F5F0F6  canvas
gold        #D7B377  fresh/live demo emphasis
bronze      #8F754F  stale/conflicting evidence
```

- Controls use 0–4 px radii; surfaces use 4–8 px.
- No decorative shadows; borders and surface contrast define hierarchy.
- Manrope headings, Inter body, DM Mono IDs/counts.
- Provider logos retain official proportions and colors.
- Gold is reserved for the fresh/live reveal, not generic CTAs.
- Every state combines color with text, icon, or shape.

## Error, loading, and recovery

- Initial load uses geometry-matched skeletons.
- Missing report shows `Verified demo report unavailable`; never fake zeroes.
- Count mismatch shows `Report out of date` and operator status.
- Graph failure preserves the task header and offers retry.
- Poll failure preserves the last safe graph and retries within the window.
- Timeout states `No live Slack update arrived in this window`; it never
  synthesizes a live node.
- If Slack exists at initial load, render it with `Already present when this
  view loaded` and skip the reveal.

## Implementation slices

| Ticket | Deliverable | Depends on | Acceptance |
| --- | --- | --- | --- |
| FE-01 | Scaffold `apps/web`, TypeScript, Tailwind, Motion, lint, test, and build scripts | None | Empty product shell builds in CI and Compose. |
| FE-02 | Add shared tokens, fonts, provider assets, shell, sidebar, top bar, and responsive navigation | FE-01 | Shell matches desktop/tablet/mobile geometry and keyboard order. |
| FE-03 | Implement typed Cortex client, runtime validation, BFF allowlist, server-only identity, and safe errors | FE-01 + backend fixtures | Browser network log contains only same-origin calls. |
| FE-04 | Build Dashboard metrics, source strip, active task, preview graph, activity, and error states | FE-02 + FE-03 | Every number exposes one report ID and timestamp. |
| FE-05 | Build Sources grid, truth badges, reveal state, proof panel, and session persistence | FE-02 + FE-03 | Reveal issues no provider/OAuth/backfill request. |
| FE-06 | Build Task Context header, synthesis, actions, evidence timeline, and initial graph | FE-02 + FE-03 + graph fixture | Pre-Slack evidence pack renders with citations/conflict. |
| FE-07 | Add live-window state machine and non-overlapping polling | FE-06 + Slack graph fixture | Success, transient error, timeout, unmount, and already-present paths pass. |
| FE-08 | Add semantic SVG interactions and citation drawer | FE-06 | Keyboard, focus return, mobile sheet, and safe excerpt tests pass. |
| FE-09 | Add bounded Motion variants and reduced-motion substitutions | FE-05 + FE-07 + FE-08 | No looped/ambient animation; reduced mode retains all meaning. |
| FE-10 | Add Playwright/axe capture matrix and presentation rehearsal | FE-04 through FE-09 | Eight required captures and 75-second product sequence pass. |

FE-01 through FE-03 establish the shared boundary. FE-04 and FE-05 may then
run in parallel with FE-06. FE-07 through FE-09 converge on Task Context;
FE-10 is the release gate.

## Testing and acceptance

Automated:

- Typecheck, lint, unit tests, and production build.
- Contract fixtures for every BFF response.
- Playwright path Dashboard → Sources → COR-123.
- Assert source-mode labels and report IDs remain visible.
- Assert `Connect` makes no OAuth/backfill/provider request.
- Assert polling starts only in the live state, never overlaps, stops on
  success/timeout/unmount, and never fabricates data.
- Keyboard/focus tests for navigation, graph, drawer, and mobile sheet.
- Axe checks plus reduced-motion and 200% zoom captures.

Acceptance:

- Three-view sequence completes within 75 seconds of the presentation.
- Every displayed count traces to one accepted report ID.
- Live Slack appears within ten seconds of backend graph availability.
- Frontend works at 1440, 1024, 768, and 375 CSS px.
- A fresh clone starts both services with one documented command.
