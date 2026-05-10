# Phase 14: Minimal Web UI

Phase 14 adds a minimal real-data web UI for audit, inspection, connector setup,
and operational status. It should help humans understand Cortex state without
replacing the agent workflow or becoming a broad chat/product app.

Phase source of truth: [`../implementation-roadmap.md`](../implementation-roadmap.md#phase-14-minimal-web-ui)

## Artifacts

- [Plan](plan.md)
- [Implementation checklist](implementation-checklist.md)
- [Test plan](test-plan.md)
- [Autoplan review](autoplan-review.md)
- [Engineering review](plan-eng-review.md)

## Operating Constraints

- UI reads real store data for core workflows.
- No static-only demo surfaces for source health, evidence, decisions,
  conflicts, connector setup, or replay/backfill status.
- UI actions reuse Phase 10 admin authorization and audit.
- UI operational surfaces reuse Phase 11 observability and Phase 13 support
  operations where available.
- The agent workflow remains primary; Phase 14 does not build a broad chat UI.
