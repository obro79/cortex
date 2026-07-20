# ADR-024 Implementation Plan: Local Evidence Control Plane

## Product thesis and explicit non-goals

The local UI is an inspection and operations surface for Cortex's agent-native
context layer. It prepares a retrieval, lets a person inspect cited evidence and
freshness, proves what was ingested/indexed, and configures the MCP tool.
Work continues in Codex, Claude Code, or Cursor through MCP.

It deliberately excludes a chat transcript, assistant avatar, model picker,
token streaming, conversation history, and a browser-first approval workflow.
A context request is an auditable record rather than a message.

## Local route tree and ownership

```text
/                         -> redirect to /ui/context
/ui/context               -> diagnostic request / result
/ui/evidence/[packId]     -> cited evidence inspector
/ui/runs/[runId]          -> deterministic fixture-pipeline proof
/ui/health                -> API/runtime health, durable health later
/ui/setup/mcp             -> stdio setup and tool inventory
/ui/evidence              -> durable evidence ledger (capability-gated)
/ui/sources               -> durable source browser (capability-gated)
/ui/connectors            -> connector control (capability-gated)
/ui/traces/[traceId]      -> durable trace (capability-gated)
```

Next runs at `127.0.0.1:3000`; FastAPI runs at `127.0.0.1:8000`. The Next BFF
at `/api/cortex/**` uses a server-only `CORTEX_API_BASE_URL`, allowlists backend
paths/methods, forwards only `content-type` and request IDs, sets timeouts, and
does not forward arbitrary browser headers/cookies. It is a temporary local
adapter for fixture `/dev`, `/demo`, and `/health` routes, then the stable
boundary for `/api/v1`.

The backend's existing HTML `/ui/*` stays frozen. Its server cookies and
presentation do not join the Next product. A later single-host deployment must
move it to `/ops/*` or retire it.

## Visual and interaction system

- 216–232px persistent sidebar, 44px command bar, dense tables/split panes,
  restrained borders/radii, and one semantic accent per status.
- Retain the scaffold's dark token system, Radix/cmdk/Lucide primitives, and
  evidence/trust vocabulary. Use sans/mono inside the control plane; editorial
  serif/chapter treatments belong only on marketing/about surfaces.
- Sidebar: **Work** (Context); **Inspect** (Evidence, Pipeline, Sources,
  Health); **Configure** (MCP Setup, Connectors); footer has local/data-mode/API
  status. Unsupported pages remain visible but disabled with a reason.
- Keyboard: Cmd/Ctrl+K command palette; `/` current filter; `N` new request;
  Cmd/Ctrl+Enter run; `E` evidence; Esc closes panels; `[` toggles sidebar.
  Single-key shortcuts do not fire in inputs.
- At less than 768px the sidebar becomes a drawer, panes stack, metadata is a
  disclosure, and dense tables become prioritized rows. Provide a skip link,
  focus-visible ring, semantic landmarks/headings, `aria-live` query/run state,
  icon labels/tooltips, non-color status labels, and reduced-motion support.

## Fixture-demo vertical slice

1. Context has a persistent `SYNTHETIC FIXTURES · NOT LIVE` disclosure backed
   by the demo/evidence contract. If unseeded, a single **Prepare demo** action
   seeds fixtures and runs the pipeline, retaining the returned run ID.
2. It shows a prepared COR-123 template; Cmd/Ctrl+Enter runs it. Do not enable
   arbitrary-query or provider-filter claims until the retrieval implementation
   supports them.
3. The result foregrounds the actual gate state, reasons, required actions,
   coverage, staleness/conflict signals, citations, and an MCP-friendly copy
   action. It never asserts fabricated freshness or permission exclusions.
4. Evidence is a two-pane claims/citations table plus metadata/coverage/gate
   rail. Citation selection opens a drawer; fixture source identifiers remain
   non-clickable.
5. Pipeline Run renders the deterministic seed-to-gate stages with status,
   duration, event ID, input/output counts, and expandable safe artifacts. Its
   title always says **Fixture pipeline**.
6. MCP Setup contains Codex/Claude Code/raw stdio snippets, tool inventory,
   copy buttons, and smoke instructions. It does not simulate a browser
   handoff or claim native agent-session resume.

Every screen covers unprepared/loading/running/completed/partial/failed/no-data
or reset-after-restart states as applicable. No fixture content is labeled live.

## Code structure

```text
src/app/(control-plane)/ui/...       route composition
src/app/api/cortex/[...path]/route.ts allowlisted BFF
src/components/control-plane/...    shell, sidebar, toolbar
src/features/context/...            request/result state machine
src/features/evidence/...
src/features/runs/...
src/features/health/...
src/features/mcp-setup/...
src/lib/api/contracts.ts            stable UI DTOs
src/lib/api/adapters/fixture.ts     dev-contract normalization
src/lib/api/adapters/durable.ts     future /api/v1 mapping
src/lib/capabilities.ts             route/action gates
```

Refactor the existing `AppShell` into the control-plane shell, preserve
`SectionShell` for marketing, evolve `EvidenceCard` into selectable evidence
rows, remove the duplicate `SourcePill`, and replace fake login actions with a
clear local-mode redirect. Snapshot the dirty user-owned scaffold before making
any implementation changes.

## API enablement order

### Fixture profile

Normalize the existing fixture seed/reset, pipeline run/read, retrieval query,
evidence-pack, demo disclosure, and readiness endpoints behind the BFF. Add
`GET /dev/state`:

```json
{
  "mode": "fixture",
  "live_data": false,
  "disclosure": "Synthetic fixtures; not live provider data.",
  "seeded": true,
  "fixture_counts": {},
  "latest_run_id": "string or null",
  "latest_run_status": "string or null",
  "latest_gate_status": "allow | warn | block | null",
  "evidence_pack_ids": []
}
```

### Durable profile

Before enabling durable pages, ship versioned `ui/bootstrap`, context request,
request/evidence read/list, source/object read/list, source-health, connector,
and trace contracts. The bootstrap returns a server-derived actor/workspace,
data mode, `live_data`, API version, and individual feature capabilities.
Context responses include request/trace IDs, status, bounded text, claims linked
to stable citation IDs, gate details, coverage, warnings, and latency. Durable
access requires SQL-backed request/evidence repositories, workspace isolation,
restart tests, and a BFF-auth/CSRF/header-trust boundary.

## Delivery tickets

| Phase | Tickets | Completion result |
| --- | --- | --- |
| Preserve/decide | UI-001, ADR-UI-001, UI-002 | scaffold checkpoint; route/data-mode/capability decision documented. |
| Foundation | UI-003–006, BE-UI-001 | dense shell, keyboard, BFF/adapters, and `GET /dev/state`. |
| Fixture demo | UI-007–011 | truthful COR-123 context/evidence/pipeline proof. |
| Operational trust | UI-012–014, QA-UI-001 | health, MCP setup, recovery/accessibility/responsive coverage. |
| Durable gate | BE-UI-002–005, SEC-UI-001 | SQL read models, versioned APIs, traces, source health, session boundary. |
| Live control plane | UI-015–018 | evidence ledger, sources, durable traces, guarded connector controls. |

## Acceptance gate

- All fixture screens disclose synthetic/not-live data and COR-123 renders the
  actual evidence pack/gate, including stale/conflicting evidence.
- Disabled modes explain why; no arbitrary query/filter, fake freshness,
  provider access, or agent-session handoff is implied.
- The UI has no chat metaphors and root opens Context. It is keyboard-operable
  and handles 375/768/1024/1440px layouts, screen-reader basics, contrast, and
  reduced motion.
- Frontend lint/typecheck/build, backend contract tests, Playwright happy/error
  paths, and axe checks pass.
- Durable routes remain capability-gated until persistence, versioned APIs,
  workspace isolation, and restart validation are complete.
