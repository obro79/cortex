# Phase 21 Plan: Production Operations

## Goal

Make it boring to run Cortex in a hosted environment.

## Scope

- Hosted environment setup.
- CI/CD deploy pipeline.
- Migration strategy.
- Backups and restore drills.
- Alerting.
- Error tracking.
- Admin support console.
- Customer support diagnostics without raw content exposure.
- Load and cost tests.
- Rollback plan.

## Exit Criteria

- Deploys are repeatable.
- Operators can monitor, support, recover, and roll back without SSH/manual
  database edits.
- Restore, rollback, and load/cost drills have recorded evidence.
