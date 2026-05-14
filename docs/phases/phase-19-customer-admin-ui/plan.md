# Phase 19 Plan: Polished Customer Admin UI

## Goal

Make Cortex operable by a customer admin without reading docs or asking the team
to run commands.

## Scope

- Real navigation and information architecture.
- Source health, evidence packs, decisions, conflicts, jobs, connector setup,
  team, billing, and settings.
- Empty/loading/error states.
- Notifications/toasts.
- Confirmation flows for destructive or expensive actions.
- Accessibility pass.
- Playwright coverage.

## Non-Goals

- No marketing site.
- No broad chat UI.
- No replacing agent workflow.
- No decorative dashboard that hides operational state.

## Exit Criteria

- Customer admin can complete core operations through the UI.
- Pages handle empty, loading, denied, stale, failed, and success states.
- Browser tests cover core happy paths and denied states.
