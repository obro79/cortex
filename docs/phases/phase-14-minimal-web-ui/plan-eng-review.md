# Phase 14 Engineering Review

## Status

Approved for implementation after review fixes.

Phase 14 should be a thin web layer over real Cortex stores and services. The
main engineering bar is preventing the UI from becoming a parallel application
with duplicated business logic, duplicated permission logic, or fake state.

## Review Findings

1. [P1] Auth/session bootstrap is under-specified.

   The plan says every page needs an actor/workspace context and allows an
   internal admin session if full user auth is missing, but it does not define
   the minimum beta-safe mechanism. Before implementation, specify the concrete
   route guard, session source, config flag, production default, CSRF posture for
   mutating UI actions, and how denied attempts are audited. Without this, the
   first UI implementation is likely to either expose pages too broadly or invent
   auth ad hoc inside route handlers.

2. [P1] Real-data read models are listed but not owned.

   Source health, evidence packs, canonical decisions, conflicts, connectors,
   and jobs are all required to read real data, but the plan does not identify
   the authoritative service/repository for each view or what happens when a
   read model does not exist yet. Add a per-surface data-source table before
   coding. Otherwise Phase 14 will either stall on missing repositories or sneak
   in static/demo adapters despite the non-goal.

3. [P2] UI action safety needs a shared action contract.

   The plan requires connector setup, source selection, re-sync, replay,
   re-embed, re-index, and decision actions to be audited, but it does not define
   one common request/result shape. Add a shared action contract with actor,
   workspace, target, idempotency key, dry-run or preview where useful,
   confirmation requirement, audit event ID, job ID, and error redaction. This
   prevents every button from inventing its own behavior.

4. [P2] Playwright smoke requires a deterministic real-store seed path.

   The test plan says the browser flow must confirm real source rows and real
   evidence packs, but it does not say how the local/staging environment gets
   that real store data. Add a seeded persistent test workspace or staging
   fixture path that writes through repositories/services rather than the
   `/dev/workbench` in-memory state. Otherwise the smoke test can become flaky
   or drift back to static fixtures.

5. [P2] Pagination and access boundaries should be acceptance criteria, not only
   performance notes.

   The review mentions bounded list pages and cross-workspace leakage as risks,
   but the main acceptance criteria do not require pagination/bounds or
   workspace isolation tests. Add both to the plan and test checklist because UI
   list pages are high-risk data exposure surfaces.

6. [P3] Accessibility is named in the sequence but not tested.

   The implementation sequence says to add accessibility checks, but the test
   plan only covers visual smoke. Add basic keyboard navigation, focus state,
   landmark, label, and contrast checks for the core pages.

## Review Fixes Applied

- [x] Add a beta-safe UI auth/session contract with production-safe defaults and
  CSRF handling for mutating actions.
- [x] Add a per-page data-source/read-model table.
- [x] Add a shared UI action result contract for audited operational actions.
- [x] Add a deterministic persistent seed path for Playwright.
- [x] Add pagination/bounded-list and workspace-isolation acceptance criteria.
- [x] Add basic accessibility checks to the test plan.

## Required Guardrails

### Real Store Data

Every core surface must read real data:

- source health,
- evidence packs,
- canonical decision history,
- conflicts/unresolved ambiguity,
- connector setup/source selection,
- backfill/replay status.

Static pages are acceptable for documentation or empty shells only, not for core
workflow proof.

### Thin Routes

Routes should:

- resolve actor and workspace,
- call a view or action service,
- render a response.

Business logic belongs in services that can be tested without a browser.

### Authorization and Audit

Any action that changes connector setup, source selection, backfill/replay,
re-embedding, re-indexing, or canonical decision state must:

- require an authorized actor,
- validate workspace scope,
- audit allowed attempts,
- audit denied attempts,
- avoid logging secrets or raw private content.

### Permission and Redaction Boundary

The UI is a data exposure surface. It must preserve the retrieval/security
permission model:

- show permission exclusion summaries,
- omit or redact disallowed content,
- avoid provider tokens and secrets,
- avoid raw private content by default,
- make hidden content explicit without leaking it.

### Frontend Scope

Prefer server-rendered HTML with small action endpoints. Add a frontend build
only if the implementation needs substantial client-side state.

The UI should be utilitarian:

- compact navigation,
- tables and filters,
- stable detail pages,
- clear status tags,
- confirmation for sensitive actions.

## Failure Modes to Test

- UI route accessible without auth.
- Non-admin actor can trigger re-sync/replay/source-selection change.
- Denied UI action is not audited.
- Evidence page displays hidden/private content.
- Source health page uses static fixture state instead of repositories.
- Backfill action blocks request until job completion.
- Long provider error text breaks layout.
- Missing workspace context leaks cross-workspace data.
- Connector secret/token appears in HTML or logs.
- Playwright smoke passes while data is missing.

## Performance Notes

- List pages should be paginated or bounded.
- Evidence detail pages should avoid loading large raw payloads.
- Source health queries should use read models or focused repository queries,
  not broad scans.
- UI actions should enqueue jobs and return references.
- Avoid auto-refresh loops that overload API or stores.

## Implementation Sequence

1. Add UI route guard, actor/workspace context, and page shell.
2. Add tested source health read model and page.
3. Add evidence-pack list/detail inspector.
4. Add canonical decision history.
5. Add conflict/ambiguity list.
6. Add connector setup/source selection pages.
7. Add backfill/replay status and safe actions.
8. Add authorization/audit tests for actions.
9. Add Playwright source health and evidence smoke.
10. Run manual visual review and record evidence.

## Review Checklist

- [ ] Core pages read real stores/services.
- [ ] No core workflow is static-only.
- [ ] Routes stay thin.
- [ ] UI actions reuse authorization and audit.
- [ ] Denied action attempts are audited.
- [ ] Raw private content is not exposed by default.
- [ ] Provider secrets never render.
- [ ] Evidence pages show permission exclusions.
- [ ] Backfill/replay actions return job references.
- [ ] Playwright covers source health and evidence inspection.
- [ ] Manual visual review covers desktop and mobile widths.
