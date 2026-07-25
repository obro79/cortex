# Cortex Component And Content Plan

Source docs: `docs/ui/README.md`, `docs/ui/page-map.md`,
`docs/ui/landing-page-content.md`, `docs/ui/app-flow.md`, and
`docs/ui/visual-reference.md`.

## Product Thesis And Constraints

Cortex is the shared context layer for agents, CLIs, MCP clients, and humans.
It connects Slack, GitHub, Linear, and repo docs so a user can ask what an agent
needs to know, receive a cited context bundle, and inspect the evidence and
source truth behind it.

The first authenticated page is `/ui/context`. It is the context console, not a
dashboard. The first-run experience should be: ask a task-oriented question,
retrieve permission-aware context, inspect evidence, then continue in MCP, CLI,
or UI.

Constraints:

- Lead with context retrieval, not metrics, activity feeds, or admin views.
- Use dense product panels and direct product language. Avoid decorative
  abstractions when a product panel can show the workflow.
- Treat MCP, CLI, and UI as equal access paths.
- Make evidence, freshness, permissions, and source coverage visible wherever a
  context answer appears.
- Raw source payloads should stay hidden by default; show normalized objects,
  chunks, metadata, and links first.
- Landing page visuals may use carefully labeled example content. Authenticated
  pages should be wired to real workspace-scoped data as soon as services exist.
- Keep admin, billing, lifecycle, and provider ACL pages later-stage unless they
  unblock the core context path.

## Page Plans

### Landing

- Route: `/`
- Primary user job: understand that Cortex gives agents live, cited company
  context through MCP, CLI, and UI, then choose login or setup.
- Content blocks:
  - Chapter `1.0 Cortex`: thesis headline, short supporting copy, `Log in` and
    `See setup` CTAs, and `FIG. 1.1` product-system map.
  - Chapter `1.1 Ask`: concrete engineering question, agent decides to call
    Cortex, mode chips for `MCP`, `CLI`, and `UI`.
  - Chapter `1.2 Retrieve`: Slack, GitHub, Linear, and repo-doc retrieval
    columns with freshness, selected-source count, and excluded-result status.
  - Chapter `1.3 Verify`: evidence pack inspector with cited chunks, source
    coverage, freshness, permission exclusions, and links to trace/source.
  - Chapter `1.4 Build`: context bundle handed back to agent, CLI, MCP, or UI
    with `fresh`, `cited`, `workspace-scoped`, and `permission-aware` labels.
  - Final CTA: login plus developer setup link.
- Reusable components needed:
  - `PublicPageShell`
  - `ChapterSection`
  - `FigureLabel`
  - `ProductSystemMap`
  - `ModeChips`
  - `ProviderColumn`
  - `EvidencePackPreview`
  - `ContextBundlePreview`
  - `CTAGroup`
- Empty/loading/error states:
  - No runtime data required for v1.
  - If auth state is loading, keep CTAs visible and disable only session-aware
    actions.
  - If login link cannot resolve, show a compact inline error near the CTA.
- Data dependencies:
  - None for initial landing content.
  - Optional auth/session state to route logged-in users to `/ui/context`.
- Acceptance checks:
  - First viewport names Cortex and shows the product-system map.
  - Landing copy does not copy Linear wording, screenshots, issue IDs, or
    customer claims.
  - Every visual depicts actual Cortex product concepts: source systems,
    retrieval, evidence, freshness, permissions, and agent handoff.
  - Primary CTA routes to `/login`; setup CTA routes to `/ui/setup` or `/docs`
    depending on implementation.

### Login

- Route: `/login`
- Primary user job: authenticate into a workspace-scoped Cortex session.
- Content blocks:
  - Auth method panel for email or provider login.
  - Workspace access note explaining that context is scoped to membership and
    permissions.
  - Compact preview of the post-login destination: `/ui/context`.
  - `Continue to workspace` CTA.
- Reusable components needed:
  - `AuthPageShell`
  - `AuthMethodForm`
  - `WorkspaceAccessNote`
  - `AuthErrorBanner`
  - `SessionRedirectNotice`
- Empty/loading/error states:
  - Loading session: show a stable progress state, not a blank page.
  - No workspace membership: explain access is required and provide request
    access path.
  - Auth failure: preserve entered email and show retry action.
  - Expired session: redirect here with a short reason and return path.
- Data dependencies:
  - Auth session.
  - Current user.
  - Workspace membership.
  - Active workspace context.
  - Initial implementation may use the current internal session path while the
    UI presents the intended product shape.
- Acceptance checks:
  - Successful login resolves workspace and lands on `/ui/context`.
  - Login never lands on a dashboard.
  - Permission copy is short and specific.
  - Error states do not expose provider internals or raw auth payloads.

### Context Console

- Route: `/ui/context`
- Primary user job: ask Cortex for the context an agent needs before work
  starts.
- Content blocks:
  - Query composer with task-oriented placeholder.
  - Source filters for Slack, GitHub, Linear, and repo docs.
  - Access mode selector for `MCP`, `CLI`, and `UI`.
  - Retrieval status strip showing selected providers, freshness, and
    permission exclusions.
  - Cited context bundle with summary, constraints, source citations, and
    confidence/freshness signals.
  - Action bar: `Get context`, `Copy for agent`, `Open evidence`,
    `Open source`, and trace link when available.
- Reusable components needed:
  - `AuthenticatedAppShell`
  - `ContextConsoleShell`
  - `ContextQueryComposer`
  - `SourceFilterBar`
  - `AccessModeSelector`
  - `RetrievalStatusStrip`
  - `ContextBundle`
  - `CitationList`
  - `PermissionExclusionSummary`
  - `FreshnessBadge`
  - `CopyForAgentButton`
- Empty/loading/error states:
  - No sources connected: show connector setup plus a sample context query.
  - No results: show active filters, health link, and suggested query revision.
  - Retrieval loading: keep query visible and stream provider-level progress if
    available.
  - Partial provider failure: return usable cited context with warning and
    failed-provider detail.
  - Permission exclusions: state count and provider without leaking restricted
    content.
- Data dependencies:
  - Retrieval service.
  - Source chunks and source objects.
  - Evidence packs.
  - Provider filters.
  - Freshness metadata.
  - Permission decision summaries.
- Acceptance checks:
  - `/ui/context` is the first authenticated page and is not labeled or treated
    as a dashboard.
  - A query can produce a visible cited context bundle.
  - Each citation can open evidence or source detail when IDs exist.
  - Copy output includes citations and constraints, not just summary prose.
  - Freshness and permission summaries remain visible above or beside results.

### Agent Trace

- Route: `/ui/traces/:trace_id`
- Primary user job: inspect what Cortex gave an agent, CLI, MCP client, or UI
  request.
- Content blocks:
  - Trace header with request origin, timestamp, workspace, and status.
  - Original query and access path.
  - Retrieval timeline: providers queried, selected evidence, excluded evidence,
    filtering decisions, and response assembly.
  - Resulting context bundle.
  - Links to evidence pack and source objects.
- Reusable components needed:
  - `TracePageShell`
  - `TraceHeader`
  - `OriginBadge`
  - `RetrievalTimeline`
  - `ProviderDecisionList`
  - `ExcludedEvidenceList`
  - `ContextBundle`
  - `EvidencePackLink`
- Empty/loading/error states:
  - Trace loading: show stable trace skeleton with route ID.
  - Trace not found: explain that the trace may have expired or belongs to
    another workspace.
  - Missing evidence pack: show trace metadata and link back to context console.
  - Partial trace: show available request records with warning.
- Data dependencies:
  - Trace metadata.
  - Retrieval request records.
  - Evidence pack records.
  - Permission decisions.
  - Source object references.
- Acceptance checks:
  - The page answers: who asked, through which access path, what was retrieved,
    what was excluded, and what was returned.
  - Excluded evidence does not expose restricted content.
  - Evidence pack CTA is present when a pack exists.
  - Trace can be reached from context result and evidence viewer.

### Evidence Viewer

- Route: `/ui/evidence/:evidence_pack_id`
- Primary user job: verify why a context answer is trustworthy.
- Content blocks:
  - Evidence header with original question, generated time, status, and source
    coverage.
  - Cited chunks grouped by provider/source object.
  - Freshness, conflict, stale-context, and permission decision rail.
  - Linked source objects and trace links.
  - Compact context bundle preview for orientation.
- Reusable components needed:
  - `EvidencePageShell`
  - `EvidenceHeader`
  - `SourceCoverageMeter`
  - `CitedChunkCard`
  - `FreshnessPanel`
  - `PermissionDecisionPanel`
  - `ConflictSignal`
  - `SourceObjectLinkList`
- Empty/loading/error states:
  - Evidence loading: show header skeleton and citation placeholders.
  - Evidence pack not found: explain evidence appears after a context request.
  - No cited chunks: show trace/request metadata and source health link.
  - Stale or conflicted evidence: mark the issue without hiding available
    citations.
- Data dependencies:
  - Evidence pack repository.
  - Retrieval request repository.
  - Source chunk repository.
  - Source object repository.
  - Provider ACL decision data where available.
- Acceptance checks:
  - Every cited chunk shows provider, source object, timestamp/freshness, and
    open-source action.
  - Permission decisions are visible and non-leaky.
  - Stale/conflict signals are visually distinct from normal citations.
  - User can navigate to the trace and source object from the pack.

### Source Browser

- Routes: `/ui/sources`, `/ui/sources/:source_id`,
  `/ui/sources/:source_id/objects/:object_id`
- Primary user job: find and inspect normalized source objects Cortex knows
  about.
- Content blocks:
  - Provider selector and source list.
  - Source detail summary with sync metadata and object counts.
  - Object list with type, title, updated time, provider, and evidence links.
  - Object detail with metadata, chunks, files, relationships, and related
    evidence.
  - Raw payload disclosure control hidden by default.
- Reusable components needed:
  - `SourcesPageShell`
  - `ProviderSelector`
  - `SourceList`
  - `SourceObjectTable`
  - `SourceObjectDetail`
  - `ChunkList`
  - `MetadataPanel`
  - `RelatedEvidenceList`
  - `RawPayloadDisclosure`
- Empty/loading/error states:
  - No sources connected: route to connector setup.
  - Source loading: preserve provider selector and list frame.
  - Source not found: show sources index link.
  - Object not found: show source detail and filter reset.
  - No chunks/files: show metadata and evidence links if present.
- Data dependencies:
  - Connector source repositories.
  - Source object repository.
  - Source file repository.
  - Source chunk repository.
  - Payload references.
- Acceptance checks:
  - User can move from provider to source to object without losing navigation
    context.
  - Raw payloads are not shown by default.
  - Object detail links back to evidence packs that cited it.
  - Source health status is reachable from source detail.

### Source Health

- Route: `/ui/health`
- Primary user job: decide whether Cortex context is fresh enough to trust and
  what to fix when it is not.
- Content blocks:
  - Health summary across connected providers.
  - Source health matrix: connection, selected scopes, sync status, cursor,
    last backfill, latest error, reauth warning, stale ACL warning.
  - Provider detail drawer or panel for latest sync/backfill context.
  - Actions: review source, reauthorize, run backfill, open connector.
- Reusable components needed:
  - `HealthPageShell`
  - `HealthSummaryStrip`
  - `SourceHealthMatrix`
  - `SyncStatusBadge`
  - `CursorPositionCell`
  - `BackfillStatusCell`
  - `ReauthWarning`
  - `StaleAclWarning`
- Empty/loading/error states:
  - No connected sources: show connector setup.
  - Health loading: show matrix skeleton by provider.
  - Worker/scheduler unavailable: show last known source status and system
    warning.
  - Stale ACL report: show action and affected provider count.
- Data dependencies:
  - Source connection repositories.
  - OAuth installation repositories.
  - Cursor repositories.
  - Backfill job repositories.
  - Provider ACL freshness reports.
  - Scheduler/worker status.
- Acceptance checks:
  - Health view explains stale or missing evidence seen in context results.
  - Every warning has a next action or a clear owner.
  - Matrix remains scannable with four providers and multiple sources.
  - Actions respect permissions and billing/plan enforcement.

### Connectors

- Route: `/ui/connectors`
- Primary user job: connect and maintain the systems agents need context from.
- Content blocks:
  - Connector cards for Slack, GitHub, Linear, and repo docs.
  - Authorization status, selected scopes, source selection summary, backfill
    status, and reauthorization warnings.
  - Setup flow entry points: connect source, select sources, run backfill,
    reauthorize.
  - Billing/plan or permission block where relevant.
- Reusable components needed:
  - `ConnectorsPageShell`
  - `ConnectorCard`
  - `AuthorizationStatusBadge`
  - `ScopeSummary`
  - `SourceSelectionSummary`
  - `BackfillProgress`
  - `ConnectorActionMenu`
  - `PlanLimitNotice`
- Empty/loading/error states:
  - No connectors authorized: show all provider cards with connect actions.
  - OAuth in progress: preserve provider card state and show callback progress.
  - Authorization failed: show retry and provider-safe error.
  - Backfill failed: show latest error and retry where allowed.
  - Permission denied: explain required role.
- Data dependencies:
  - Connector setup services.
  - OAuth installation repositories.
  - Source selection repositories.
  - Billing/plan enforcement.
  - Permission checks.
- Acceptance checks:
  - Each provider card has an explicit status and next action.
  - Reauthorization warnings are impossible to miss.
  - Connector setup can lead directly back to `/ui/context`.
  - Sensitive OAuth details are never shown raw.

### Developer Setup

- Route: `/ui/setup` or `/docs`
- Primary user job: configure MCP, CLI, or UI use of Cortex.
- Content blocks:
  - Access path tabs: `MCP`, `CLI`, `UI`.
  - MCP config snippet with safe redaction.
  - CLI command examples for context retrieval.
  - UI link to `/ui/context`.
  - Example agent prompt that asks for context before editing code.
  - Test request action when supported.
- Reusable components needed:
  - `SetupPageShell`
  - `AccessPathTabs`
  - `SetupSnippet`
  - `CopyConfigButton`
  - `CommandExample`
  - `RedactedTokenField`
  - `TestContextRequest`
- Empty/loading/error states:
  - Setup metadata loading: keep tabs visible with skeleton snippet.
  - Missing token/API key support: explain current internal path and safe next
    step.
  - Copy failure: expose manual selection affordance.
  - Test request failure: show source health and connector links.
- Data dependencies:
  - Workspace config.
  - API keys or token references where supported.
  - Safe redacted setup metadata.
- Acceptance checks:
  - User can copy MCP config without exposing secrets in the UI.
  - CLI examples are runnable once the backend supports them.
  - Setup page points users back to context console, not a generic dashboard.
  - Example agent prompt includes evidence and permission expectations.

### Later Settings/Admin

- Routes: `/ui/settings`, `/ui/team`, `/ui/billing`,
  `/ui/lifecycle`, `/ui/provider-acls`
- Primary user job: administer workspace, team, lifecycle, billing, and provider
  ACL concerns after the core context flow works.
- Content blocks:
  - Settings: workspace name, defaults, retention summary.
  - Team: members, roles, invitations, permission explanation.
  - Billing: plan status, limits, billing portal link.
  - Lifecycle: retention policy, deletion/export requests.
  - Provider ACLs: provider principal mappings and stale mapping warnings.
  - Audit log links where needed.
- Reusable components needed:
  - `AdminPageShell`
  - `SettingsForm`
  - `MemberTable`
  - `RoleBadge`
  - `BillingStatusPanel`
  - `RetentionPolicyPanel`
  - `LifecycleRequestTable`
  - `ProviderPrincipalMappingTable`
  - `AuditLogLink`
- Empty/loading/error states:
  - No admin permission: show read-only summary or route back to context.
  - Billing unavailable: show current plan metadata if safe.
  - No lifecycle requests: show empty table with request action.
  - No provider mappings: show setup explanation and connector link.
- Data dependencies:
  - Tenancy repositories.
  - Billing repositories.
  - Lifecycle repositories.
  - Provider principal mapping repositories.
  - Audit logs.
- Acceptance checks:
  - These routes do not block the first context-console implementation.
  - Admin actions are permission-gated.
  - Provider ACL pages make stale mappings visible without exposing restricted
    source content.
  - Settings never become the default post-login destination.

## Shared Component Inventory

### Primitives

- `Button`: primary, secondary, ghost, destructive, disabled, loading.
- `IconButton`: tool actions with tooltip labels.
- `Input`, `Textarea`, `Select`, `Checkbox`, `Toggle`, `SegmentedControl`.
- `Tabs`: access paths and detail panels.
- `Badge`: provider, freshness, status, role, origin, permission.
- `Tooltip`, `Popover`, `Drawer`, `Modal`.
- `Skeleton`, `Spinner`, `ProgressBar`.
- `InlineAlert`, `ErrorBanner`, `EmptyState`.
- `CodeBlock`, `CopyButton`.
- `Breadcrumbs`, `Pagination`, `SearchField`.

### Product Components

- `ModeChips` for `MCP`, `CLI`, and `UI`.
- `ProviderIconSet` for Slack, GitHub, Linear, and repo docs.
- `ContextQueryComposer`.
- `SourceFilterBar`.
- `AccessModeSelector`.
- `RetrievalStatusStrip`.
- `ContextBundle`.
- `CitationList` and `CitedChunkCard`.
- `EvidencePackPreview`.
- `PermissionExclusionSummary`.
- `FreshnessBadge` and `FreshnessPanel`.
- `SourceCoverageMeter`.
- `TraceHeader` and `RetrievalTimeline`.
- `ConnectorCard`.
- `SourceHealthMatrix`.
- `SetupSnippet` and `CopyConfigButton`.

### Page Shells

- `PublicPageShell`: landing navigation, public CTAs, product-story layout.
- `AuthPageShell`: centered auth flow with workspace access context.
- `AuthenticatedAppShell`: app navigation ordered as Context, Sources,
  Evidence, Health, Connectors, Setup.
- `ContextConsoleShell`: query/result layout with sticky action region.
- `DetailPageShell`: header, metadata rail, main content, related links.
- `AdminPageShell`: later-stage admin navigation and permission guard.

### Data Display

- `SourceObjectTable`.
- `SourceList`.
- `SourceObjectDetail`.
- `ChunkList`.
- `MetadataPanel`.
- `RelatedEvidenceList`.
- `ProviderDecisionList`.
- `ExcludedEvidenceList`.
- `HealthSummaryStrip`.
- `SyncStatusBadge`.
- `CursorPositionCell`.
- `BackfillStatusCell`.
- `ScopeSummary`.
- `AuthorizationStatusBadge`.
- `LifecycleRequestTable`.
- `ProviderPrincipalMappingTable`.

## Parallel Workstreams

These streams can move in parallel after shared primitives and route shells are
named. Keep shared components reviewed together so pages do not fork visual or
data-state patterns.

- Workstream A: Landing, login, and developer setup content. Owns public
  product story, auth entry, setup snippets, and safe redaction patterns.
- Workstream B: Context console, evidence viewer, and agent trace. Owns the
  core ask, retrieve, cite, inspect loop and should land first for product
  value.
- Workstream C: Source browser, source health, and connectors. Owns source
  trust, setup, backfill, reauth, and missing/stale-context recovery.
- Workstream D: Later settings/admin. Owns permission-gated admin surfaces only
  after the core context loop works.

## Autoplan-Style Review

### CEO Findings And Decisions

- Finding: The strongest product wedge is not a dashboard; it is a fast path
  from task question to cited context bundle.
- Decision: Keep `/ui/context` as the first authenticated page and make every
  supporting page feed back into context retrieval, evidence, or source trust.
- Finding: Landing should prove the product with workflow visuals instead of
  broad "knowledge" claims.
- Decision: Use the Linear Intake rhythm only as structure: numbered chapters,
  figure labels, short claims, dense product panels, and no copied assets or
  wording.

### Design Findings And Decisions

- Finding: The product needs quiet, scannable operational UI. Oversized
  marketing sections or generic dashboards would dilute the point.
- Decision: Use dense panels, tables, rails, badges, and direct product nouns:
  evidence, source, trace, freshness, permission.
- Finding: Trust signals can become scattered if each page invents its own
  treatment.
- Decision: Reuse freshness, permission, citation, and source coverage
  components across context, trace, evidence, source, and health pages.

### Eng Findings And Decisions

- Finding: The same backend concepts appear across pages: retrieval requests,
  evidence packs, source objects, chunks, provider ACL decisions, cursors, and
  backfills.
- Decision: Build shared product components around those domain objects instead
  of page-local one-offs.
- Finding: Several pages depend on services that may land after the scaffold.
- Decision: Define explicit empty/loading/error states now so incomplete data
  paths degrade to connector setup, health checks, or context-console links.

### DX Findings And Decisions

- Finding: The fastest implementation path is a predictable component inventory
  with clear acceptance checks per route.
- Decision: Treat this doc as the UI build checklist. Each route is shippable
  when its user job, states, data dependencies, and acceptance checks pass.
- Finding: Developer setup must serve both product evaluation and real agent
  integration.
- Decision: Setup content should be copyable, redacted, and routed back to
  `/ui/context` for a test request.

## Implementation Order

1. Build shared primitives and `AuthenticatedAppShell`.
2. Build `/ui/context` with sample or service-backed context result states.
3. Build evidence viewer and trace detail links from context results.
4. Build source browser and source health to support trust debugging.
5. Build connectors and developer setup as direct support flows.
6. Build landing page product visuals using the same component vocabulary.
7. Defer settings/admin until the context, evidence, source, health, connector,
   and setup loops are working.
