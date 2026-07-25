# 2026-05-14 Production Activation Local Evidence

Environment: local
Operator: Codex
Scope: lifecycle queueing, provider ACL ingestion, Stripe route activation, and
RBAC route audit

## Status

This is not staging evidence. It records local implementation and validation
evidence for the production activation blockers, and keeps live/staging drill
gaps explicit.

## Lifecycle Deletion And Export

Local evidence:

- Added lifecycle API routes for deletion/export request, status, lease,
  execute, and retry.
- Added an SQL lifecycle worker role that leases queued jobs and executes
  deletion/export repositories in a transaction.
- Wired Qdrant point deletion through the repository-backed lifecycle executor.
- Focused lifecycle tests passed for service execution, queue retries, and API
  routes.

Residual risk:

- Staging deletion/export drills have not been run against deployed SQL, payload
  storage, and Qdrant.

## Provider ACL Ingestion

Local evidence:

- Added provider ACL collectors for Slack channel members, GitHub repository
  collaborators, and Linear team members.
- Added hashed authenticated user-to-provider-principal mappings with SQL
  persistence.
- Added stale/missing freshness reporting with safe alert payloads.
- Focused provider ACL ingestion and mapping tests passed.

Residual risk:

- Scheduled production/staging ACL snapshot jobs are not deployed or proven yet.
- Freshness alerts have not been observed in staging.

## Stripe Activation

Local evidence:

- Added customer-facing checkout and portal routes guarded by
  `BILLING_ADMIN`.
- Added Stripe webhook route with signature verification and idempotent event
  recording.
- Added staging/production activation runbook with required secret names and
  smoke evidence fields.
- Focused billing route and webhook tests passed.

Residual risk:

- Live/staging Stripe secrets were not available in this workspace.
- Checkout, portal, and webhook smoke tests were not run against Stripe.

## RBAC Audit

Local evidence:

- Added route-by-route backend public/admin RBAC audit.
- Added a hard guard that rejects dev workbench routes outside `local` or
  `test` environments.
- Added a static docs test for the RBAC audit.

Residual risk:

- Provider webhook route hardening has local regression coverage for GitHub
  source-connection binding and Slack unmapped-team ignore behavior. Staging
  provider delivery evidence is still required before broad enterprise launch.

## Validation

- `uv run pytest`: 414 passed.
- `uv run ruff check .`: passed.
- `uv run ruff format --check .`: passed.
- `uv run mypy src`: passed.
- `docker compose config`: passed.
- `docker compose --profile lifecycle config`: passed.
- `uv run alembic heads`: one head,
  `0016_provider_principal_mappings`.
- `uv run alembic upgrade head --sql`: passed.
- `uv run alembic downgrade 0016_provider_principal_mappings:0013_lifecycle_persistence --sql`:
  passed.
- `git diff --check`: passed.
