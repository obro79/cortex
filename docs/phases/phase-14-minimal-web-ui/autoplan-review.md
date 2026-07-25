# Phase 14 Autoplan Review

## Verdict

Proceed as a minimal audit/admin UI, not as a customer application rewrite.
Phase 14 is valuable because it gives humans a reliable way to inspect real
Cortex state, verify evidence, and operate connectors without ad hoc scripts.

## CEO Review

Mode: hold scope.

The 10-star version of this phase is not a polished chat product. It is a
trust-building control surface for design partners and operators:

- source freshness is obvious,
- evidence is inspectable,
- canonical decisions are traceable,
- conflicts are visible,
- connector setup is manageable,
- backfills and replays are not hidden in logs.

Do not expand into broad collaboration UI, dashboards for every metric, or
enterprise admin features. The agent workflow remains the product center.

## Design Review

Phase 14 needs a designer's eye because it is the first real-data web surface
beyond the dev workbench.

Design principles:

- dense but calm operational layout,
- tables for scan-heavy pages,
- detail pages for evidence and decisions,
- clear status labels and timestamps,
- no landing page,
- no decorative hero,
- no static demo data pretending to be system state.

The most important design problem is trust. The UI must make it clear what is
fresh, stale, failed, hidden by permissions, or unresolved.

## Engineering Review

The plan is technically sound if the UI is a thin layer over existing services:

- routes resolve actor/workspace context,
- services provide read models,
- actions reuse authorization and audit,
- templates render summaries,
- tests prove real data paths.

Risks:

- route handlers become business-logic dumps,
- static/demo pages slip in for hard surfaces,
- UI exposes provider secrets or raw private content,
- connector actions bypass Phase 10 audit,
- Playwright coverage only checks page load, not real data.

## DX Review

The UI should be easy to run locally and easy to inspect in tests.

Requirements:

- one clear command to run the API with UI enabled,
- seed or fixture path for local browser smoke tests,
- predictable selectors for Playwright,
- stable URLs for support/debug conversations,
- no heavy frontend build unless justified by implementation reality.

## Decision Log

- Use a minimal server-rendered UI unless implementation proves a stronger need.
- Keep the existing `/dev/workbench` separate from the Phase 14 real-data UI.
- Require all core pages to read real repositories/services.
- Require admin authorization and audit for setup, replay, re-sync, and repair
  actions.
- Require Playwright smoke coverage for source health and evidence-pack
  inspection.

## Approval Conditions

- The plan must not include a broad chat UI.
- The implementation must include real-data source health and evidence-pack
  inspection before polish.
- No core page may be static-only.
- UI action tests must cover allowed and denied paths.
- Manual visual review evidence must be recorded before closeout.
