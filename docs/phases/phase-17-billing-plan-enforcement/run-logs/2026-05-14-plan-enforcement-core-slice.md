# 2026-05-14 Plan Enforcement Core Slice

## Completed

- Added organization-scoped billing customer and subscription domain models.
- Added plan entitlement and usage meter models for seats, workspaces, sources,
  indexed objects, retrievals, storage, and model calls.
- Added an in-memory billing repository for local/test enforcement.
- Added a plan enforcement service that returns allow/deny decisions for API
  and worker/job callers and records usage on allowed actions.
- Added invite-only and free-trial default entitlements.

## Validation

```bash
uv run pytest tests/billing/test_plan_enforcement.py
uv run ruff check src/cortex/billing tests/billing/test_plan_enforcement.py
```

Result: both passed.

## Remaining Phase 17 Work

- Add SQL persistence and migration for billing state.
- Add Stripe customer creation, checkout, portal, webhook verification, and
  webhook idempotency.
- Wire enforcement into concrete API and worker entrypoints.
- Add billing admin UI and audit events for billing admin actions.
