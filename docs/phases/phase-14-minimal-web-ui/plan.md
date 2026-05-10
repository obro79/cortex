# Phase 14 Plan: Minimal Web UI

## Goal

Build a minimal real-data web UI for audit and inspection. The UI should make
source freshness, evidence packs, canonical decisions, unresolved conflicts,
connector setup, source selection, and replay/backfill status understandable to
humans without replacing the agent workflow.

The UI is successful when an operator or design-partner admin can answer:

- Are my sources connected and fresh?
- What evidence did Cortex use for this answer or gate decision?
- Which canonical decisions are approved, proposed, superseded, or rejected?
- What conflicts or unresolved ambiguities still need human review?
- What backfills, replays, or repair jobs are running or failed?

## Inputs

- [`../implementation-roadmap.md`](../implementation-roadmap.md#phase-14-minimal-web-ui)
- [`../../architecture/review.md`](../../architecture/review.md)
- [`../../architecture/handbook.md`](../../architecture/handbook.md#dev-workbench-strategy)
- [`../phase-01-dev-workbench-fixtures/plan.md`](../phase-01-dev-workbench-fixtures/plan.md)
- [`../phase-10-permissions-security/plan.md`](../phase-10-permissions-security/plan.md)
- [`../phase-11-observability-operations/plan.md`](../phase-11-observability-operations/plan.md)
- [`../phase-13-layer-later-platform/plan.md`](../phase-13-layer-later-platform/plan.md)

## Non-Goals

- Do not build a broad chat UI.
- Do not replace MCP/API agent workflows.
- Do not build a public marketing site.
- Do not add a heavy frontend stack unless the existing server-rendered approach
  becomes a real blocker.
- Do not expose raw private content by default.
- Do not implement enterprise IAM or full provider-native ACL management in the
  UI.
- Do not use static fixture data for the core Phase 14 surfaces.

## Product Shape

Phase 14 should feel like a compact operations console:

- dense, scannable tables,
- plain status labels,
- clear timestamps and freshness windows,
- filterable lists,
- detail drawers or pages for evidence and decisions,
- explicit confirmations for expensive or sensitive actions,
- no decorative landing page.

The UI should make the first wow workflow inspectable, but it should read from
the same stores and services used by real connectors, retrieval, canonical
memory, and support operations.

## Architecture

Use the existing FastAPI app as the host. Prefer server-rendered pages with
small JSON endpoints for actions and refreshes. Introduce templates/static
assets only if that keeps route code thin.

```text
Browser
  |
  v
FastAPI web routes
  |
  +--> Session/auth/admin actor resolution
  |
  +--> View services
  |       +--> source health read models
  |       +--> evidence pack read models
  |       +--> canonical decision read models
  |       +--> conflict/ambiguity read models
  |       +--> backfill/replay/job read models
  |
  +--> Action services
          +--> connector setup/source selection
          +--> re-sync/backfill/replay requests
          +--> Phase 10 authorization
          +--> audit log
```

Recommended module boundaries:

```text
src/cortex/api/routes/ui.py
src/cortex/ui/
  __init__.py
  auth.py
  views.py
  source_health.py
  evidence.py
  decisions.py
  conflicts.py
  connectors.py
  jobs.py
  render.py
```

Keep routes thin. Route handlers should resolve actor/workspace context, call a
view/action service, and render a template or return a small response.

## Auth, Session, and CSRF Contract

Phase 14 must define one UI guard before any page-specific routes land.

Minimum beta-safe contract:

- UI routes are disabled unless `CORTEX_UI_ENABLED=true`.
- The production default is disabled unless the deployment explicitly enables
  the UI.
- Every UI request resolves a `UiActorContext` with actor ID, workspace ID,
  roles/capabilities, session ID, and request trace ID.
- Local/staging may use an internal admin session mechanism, but it must be
  gated by a separate explicit setting such as
  `CORTEX_INTERNAL_ADMIN_SESSION_ENABLED=true`.
- Internal admin sessions are never enabled implicitly by `cortex_env`.
- Mutating UI actions require a CSRF token tied to the session.
- Mutating UI actions use POST and never GET.
- Missing, expired, or invalid sessions receive a denied state without leaking
  whether a workspace/resource exists.
- Denied sensitive actions are audited with actor/session if known, workspace if
  known, action, target, reason, result, and trace ID.

The route guard should be centralized under `src/cortex/ui/auth.py`; route
handlers should not inspect raw headers/cookies directly except through that
guard.

## Real-Data Read Model Ownership

Each core page needs an explicit data source. If a read model is missing, the
implementation must add a real repository/service-backed read model or defer the
page with a documented gap. It must not use static UI fixtures for core
workflows.

| Surface | Authoritative data source | Missing-read-model rule |
| --- | --- | --- |
| Source health | Phase 11/13 source health, connector state, cursors, deadletters, and support job summaries | Add `SourceHealthViewService` over real repositories before rendering the page. |
| Evidence-pack inspector | Retrieval/evidence-pack repositories and gate result records | Add `EvidencePackViewService`; no fallback to `/dev/workbench` evidence. |
| Canonical decision history | Phase 7 canonical memory repository/service and audit records | Add `CanonicalDecisionViewService`; actions only if Phase 7/10 services are available. |
| Conflict and ambiguity list | Context gate conflict/staleness signals, evidence records, and canonical decision proposals | Add a read model that derives unresolved rows from real gate/evidence data. |
| Connector setup/source selection | Connector repositories, OAuth/install state, source allowlists, and permission state | Add provider-specific adapters over implemented connector services only. |
| Backfill/replay status | Phase 11/13 job, deadletter, replay, and support-operation records | Add `JobStatusViewService`; actions enqueue work and return job references. |

## Shared UI Action Contract

All mutating UI actions should use one request/result pattern so buttons behave
consistently and auditing is complete.

Action request fields:

- actor context,
- workspace ID,
- action name,
- target type and target ID,
- idempotency key,
- CSRF token,
- confirmation token for sensitive or expensive operations,
- optional dry-run or preview mode,
- reason/comment where useful for audit.

Action result fields:

- result: `accepted`, `denied`, `queued`, `completed`, or `failed`,
- audit event ID,
- job ID where work is asynchronous,
- trace ID,
- target summary,
- user-safe message,
- redacted error code/details.

Actions should not return raw provider payloads, secrets, tokens, or private
content. Long-running actions should enqueue work and return a job reference.

## Surfaces

### 1. Source Health

Shows each workspace source and connector:

- provider,
- source name and scope,
- enabled/disabled state,
- last sync/backfill time,
- freshness status,
- last error summary,
- event/cursor/deadletter counts where available,
- permission or reauthorization warnings.

Actions:

- start re-sync/backfill,
- disable/enable source where supported,
- open source detail.

### 2. Evidence-Pack Inspector

Shows real evidence packs produced by retrieval/gate workflows:

- query/request metadata,
- gate status and reasons,
- cited sources,
- source coverage,
- stale/conflict signals,
- permission exclusions summary,
- compact cited text snippets only where allowed.

The inspector must link evidence back to source objects, chunks, canonical
decisions, and retrieval traces where available.

### 3. Canonical Decision History

Shows human-approved canonical memory:

- proposed decisions,
- approved decisions,
- rejected decisions,
- superseded decisions,
- scope and target,
- actor and timestamp,
- linked evidence references.

Actions:

- view decision detail,
- approve/reject/edit if Phase 7/10 services expose those actions safely,
- inspect supersession chain.

### 4. Conflict and Ambiguity List

Shows unresolved conflicts and stale context requiring human review:

- conflict type,
- affected workspace/source/scope,
- detected evidence,
- current gate impact,
- last seen timestamp,
- suggested next action.

This page should prioritize work, not invent automated resolution.

### 5. Connector Setup and Source Selection

Shows setup flows for Slack, Linear, GitHub, and repo docs where implemented:

- connection status,
- OAuth/install or import status,
- selected source scopes,
- source allowlist choices,
- reauthorization requirements,
- webhook/backfill status.

Actions must be permission-gated and audited.

### 6. Backfill and Replay Status

Shows operational jobs:

- current backfills,
- replay requests,
- deadletter status,
- force re-embed/re-index jobs,
- job result and failure reason,
- trace IDs or audit IDs.

Actions should enqueue work and return job references rather than blocking UI
requests.

## Auth and Permissions

Phase 14 must not rely on obscurity. Every page and action needs an actor and a
workspace context.

Minimum behavior:

- unauthenticated users cannot access the UI,
- non-admin actors cannot perform security-sensitive setup or repair actions,
- denied attempts are audited,
- UI only displays source/evidence details allowed by the actor's permissions,
- pages avoid raw private content by default.

If full user auth is not implemented yet, Phase 14 may use a clearly documented
internal admin session mechanism for local/beta only, but the route boundaries
must be ready to swap to real auth.

## Persistent Test Seed Path

Playwright and route tests need a deterministic real-store seed path that writes
through repositories/services, not the in-memory `/dev/workbench` state.

Seed requirements:

- creates a test workspace,
- creates at least one source connection and source object,
- persists source health/freshness state,
- persists at least one evidence pack and gate result,
- persists at least one canonical decision in a non-empty state,
- persists at least one conflict/staleness row or equivalent derived signal,
- persists one backfill/replay/job status row,
- creates admin and non-admin actors for auth tests,
- can reset only the test workspace without touching other data.

The seed path may reuse deterministic fixture content from the dev workbench, but
it must persist through the same repositories/services used by the Phase 14 UI.

## Data Rules

- Read from repositories/services, not hardcoded UI fixtures.
- Use redacted summaries by default.
- Show IDs, timestamps, provider, status, and reason fields consistently.
- Prefer stable URLs that can be copied into support/debug conversations.
- Preserve trace IDs, audit IDs, job IDs, and evidence-pack IDs in detail pages.

## Implementation Sequence

1. Define UI route guard, actor/workspace context, CSRF handling, and page shell.
2. Add deterministic persistent test seed path.
3. Add shared UI action request/result contract.
4. Add source health read model and page.
5. Add evidence-pack list/detail inspector.
6. Add canonical decision list/detail pages.
7. Add conflict/ambiguity list.
8. Add connector setup/source selection pages and actions.
9. Add backfill/replay/job status page and actions.
10. Add visual polish, responsive layout, empty/error/loading states,
    pagination, workspace isolation, and accessibility coverage.
11. Add Playwright smoke coverage.
12. Record manual visual testing evidence.

## Commit Cadence

1. `phase 14: add ui route guard and page shell`
2. `phase 14: add persistent ui smoke seed`
3. `phase 14: add shared ui action contract`
4. `phase 14: add source health page`
5. `phase 14: add evidence pack inspector`
6. `phase 14: add canonical decision history`
7. `phase 14: add conflict and ambiguity list`
8. `phase 14: add connector setup and source selection`
9. `phase 14: add backfill and replay status`
10. `phase 14: add ui action audit coverage`
11. `phase 14: add playwright smoke coverage`
12. `phase 14: document manual visual review`

## Acceptance Criteria

- Playwright smoke flow covers source health and evidence-pack inspection.
- Playwright uses a deterministic persistent real-store seed path.
- UI reads real store data for all core surfaces.
- No core Phase 14 page is static-only.
- UI routes are disabled by default unless explicitly enabled.
- Mutating UI actions require CSRF protection.
- Security-sensitive actions require admin authorization.
- Allowed and denied UI actions are audited.
- List pages are bounded or paginated.
- Workspace isolation tests prove one workspace cannot view another workspace's
  UI data.
- Evidence and source pages respect permission/redaction boundaries.
- Connector setup/source selection works for implemented providers.
- Backfill/replay status shows real job state.
- UI has useful empty, error, and stale states.
- Core pages pass basic accessibility checks for keyboard navigation, focus,
  landmarks, labels, and contrast.
- Phase docs include manual visual testing notes before closeout.
