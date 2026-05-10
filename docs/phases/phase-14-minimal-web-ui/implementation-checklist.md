# Phase 14 Implementation Checklist

## Prerequisites

- [ ] Phase 10 admin authorization and audit paths exist.
- [ ] Phase 11 source health, deadletter, replay, and observability data are
      available enough to display.
- [ ] Phase 13 support operations expose safe action services or endpoints.
- [ ] Real repositories/services exist for source health, evidence packs,
      canonical decisions, conflicts, connectors, and jobs.
- [ ] Decide whether Phase 14 uses server-rendered templates, existing manual
      HTML rendering, or a minimal static asset layer.
- [ ] Define the per-page real-data read-model owner before building each page.
- [ ] Define the deterministic persistent test seed path.

## UI Shell and Guard

- [ ] Add UI route module.
- [ ] Add `CORTEX_UI_ENABLED` or equivalent production-safe feature flag.
- [ ] Add internal admin session flag that is disabled by default.
- [ ] Add actor/workspace resolution.
- [ ] Add centralized `UiActorContext`.
- [ ] Add CSRF token issuance and validation for mutating actions.
- [ ] Add unauthenticated/unauthorized handling.
- [ ] Audit denied sensitive UI actions.
- [ ] Add common page shell and navigation.
- [ ] Add consistent status, timestamp, ID, and error display components.
- [ ] Add responsive layout for desktop and narrow screens.
- [ ] Add stable URLs for list/detail pages.
- [ ] Ensure routes do not read raw auth headers/cookies outside the centralized
      guard.

## Persistent Real-Store Seed

- [ ] Add a seed/reset path for a dedicated UI smoke-test workspace.
- [ ] Seed source connection state through repositories/services.
- [ ] Seed source health/freshness state through repositories/services.
- [ ] Seed at least one evidence pack and gate result through real services or
      repositories.
- [ ] Seed at least one canonical decision through canonical memory service.
- [ ] Seed at least one conflict/staleness signal through real gate/evidence
      data.
- [ ] Seed at least one backfill/replay/job status row.
- [ ] Seed admin and non-admin actors.
- [ ] Reset only the test workspace.
- [ ] Prove Playwright does not depend on `/dev/workbench` in-memory state.

## Shared UI Action Contract

- [ ] Add common action request type with actor, workspace, action, target,
      idempotency key, CSRF token, confirmation token, and optional dry-run.
- [ ] Add common action result type with result, audit event ID, job ID, trace
      ID, target summary, user-safe message, and redacted error details.
- [ ] Apply the contract to connector setup/source selection actions.
- [ ] Apply the contract to re-sync/backfill/replay actions.
- [ ] Apply the contract to re-embed/re-index actions where supported.
- [ ] Apply the contract to canonical decision actions where supported.
- [ ] Ensure long-running actions enqueue work and return job references.
- [ ] Ensure action responses do not include provider tokens, secrets, or raw
      private content.

## Source Health

- [ ] Add source health read model.
- [ ] Identify the authoritative source health repositories/services.
- [ ] Show provider, source, scope, state, freshness, last sync, and last error.
- [ ] Show cursor, event, deadletter, and permission warning summaries where
      available.
- [ ] Add source detail page.
- [ ] Add permission-gated re-sync/backfill action.
- [ ] Audit allowed and denied actions.
- [ ] Add empty, loading, stale, and error states.
- [ ] Add pagination or bounded list behavior.
- [ ] Add workspace isolation coverage.

## Evidence-Pack Inspector

- [ ] Add evidence-pack list page.
- [ ] Identify the authoritative evidence-pack repositories/services.
- [ ] Add evidence-pack detail page.
- [ ] Show query/request metadata.
- [ ] Show gate status and reasons.
- [ ] Show cited sources and source coverage.
- [ ] Show stale/conflict signals.
- [ ] Show permission exclusion summary.
- [ ] Link to source objects, chunks, traces, and canonical decisions where
      available.
- [ ] Redact or omit raw private content by default.
- [ ] Add pagination or bounded list behavior.
- [ ] Add workspace isolation coverage.

## Canonical Decision History

- [ ] Add decision list page with status filters.
- [ ] Identify the authoritative canonical decision repositories/services.
- [ ] Add decision detail page.
- [ ] Show proposal, approval/rejection, supersession, scope, actor, and
      timestamps.
- [ ] Link decisions to supporting evidence.
- [ ] Add approve/reject/edit actions only if existing services safely support
      them.
- [ ] Audit allowed and denied decision actions.
- [ ] Show supersession chain clearly.
- [ ] Add pagination or bounded list behavior.
- [ ] Add workspace isolation coverage.

## Conflict and Ambiguity List

- [ ] Add unresolved conflict read model.
- [ ] Identify the authoritative conflict/staleness repositories/services or
      derivation query.
- [ ] Show affected scope, conflict type, evidence references, gate impact, and
      last seen timestamp.
- [ ] Add filters by provider, scope, conflict type, and severity.
- [ ] Link to evidence packs and canonical decision proposals.
- [ ] Avoid automatic resolution unless a prior phase service already defines
      the action.
- [ ] Add pagination or bounded list behavior.
- [ ] Add workspace isolation coverage.

## Connector Setup and Source Selection

- [ ] Add connector status overview.
- [ ] Identify the authoritative connector setup/source selection
      repositories/services per provider.
- [ ] Add provider detail pages for implemented providers.
- [ ] Show OAuth/install/import state.
- [ ] Show selected source scopes and allowlist status.
- [ ] Add permission-gated source selection changes.
- [ ] Add reauthorization state and action where supported.
- [ ] Audit setup, selection, disable, enable, and reauthorization actions.
- [ ] Ensure responses do not expose tokens or provider secrets.
- [ ] Add workspace isolation coverage.

## Backfill and Replay Status

- [ ] Add job/backfill/replay read model.
- [ ] Identify the authoritative job/deadletter/replay repositories/services.
- [ ] Show running, queued, completed, failed, and skipped jobs.
- [ ] Show deadletter summaries.
- [ ] Add permission-gated replay action.
- [ ] Add permission-gated force re-embed/re-index action where supported.
- [ ] Show job IDs, trace IDs, audit IDs, and failure reasons.
- [ ] Return job references for long-running actions.
- [ ] Add pagination or bounded list behavior.
- [ ] Add workspace isolation coverage.

## Visual and Interaction Quality

- [ ] Tables stay readable on desktop and mobile.
- [ ] Long provider names, URLs, source names, and errors wrap without overlap.
- [ ] Buttons use clear action labels and disabled states.
- [ ] Sensitive or expensive actions have confirmation states.
- [ ] Empty states explain what data is missing without pretending data exists.
- [ ] Error states are actionable and do not leak secrets.
- [ ] Page load and action latency are acceptable with representative data.
- [ ] Keyboard navigation reaches all core controls.
- [ ] Focus states are visible.
- [ ] Pages have useful landmarks and labels.
- [ ] Text and status indicators meet contrast requirements.

## Closeout

- [ ] Add Playwright smoke tests.
- [ ] Add Playwright seed/reset setup for real-store data.
- [ ] Add focused route/service tests.
- [ ] Add authorization/audit tests for UI actions.
- [ ] Add workspace isolation tests.
- [ ] Add pagination/bounded-list tests.
- [ ] Add accessibility checks.
- [ ] Run manual visual review on desktop and mobile widths.
- [ ] Capture screenshots or notes under this phase directory.
- [ ] Update phase docs with implementation deviations and residual risks.
