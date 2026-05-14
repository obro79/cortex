# Enterprise Readiness Launch Checklist

## Gate Status

Current status: invite-only beta, not broad self-serve enterprise rollout.

## Required Evidence

- Tenant isolation: Phase 15 tenant identity, public tenant context, and worker
  scope run logs.
- Auth/onboarding: Phase 15 public auth context evidence; onboarding flow is
  still a launch blocker.
- Connector setup: Phase 16 shared setup service evidence plus hardened public
  API routes for source listing, selection, and backfill. Customer-facing UI
  setup remains a launch blocker.
- Billing: Phase 17 plan enforcement core evidence plus SQL-backed billing and
  Stripe verification/session boundaries. Live checkout/portal smoke evidence and
  customer plan-management routes are still launch blockers.
- RBAC: Phase 18 role/permission matrix evidence; hardened connector admin
  routes enforce membership, workspace match, and permissions. Full public admin
  surface coverage still needs audit.
- Admin UI: Phase 19 navigation foundation evidence; several pages remain
  placeholder states.
- Compliance: Phase 20 lifecycle core evidence plus repository-backed
  deletion/export executor foundations. SQL lifecycle persistence and async
  service wiring are present, but production queueing and drill evidence remain
  incomplete.
- Operations: Phase 21 production operations runbook evidence; staging drills
  still need real results.

## Security Review Checklist

- Public routes reject internal actor headers.
- Public routes resolve tenant context before customer data access.
- Support diagnostics do not include raw content, provider tokens, session
  tokens, private URLs, or unredacted customer object IDs.
- Audit logs hash target IDs where raw IDs are not needed.
- Connector setup metadata is redacted before audit persistence.
- Lifecycle deletion tombstones store target hashes.
- Secrets are runtime-only and never committed to images, docs, or run logs.

## Launch Blockers

- Complete Phase 15 onboarding routes and browser coverage.
- Complete Slack and GitHub customer setup UI flows.
- Validate Stripe checkout, webhook verification, and billing portal in staging.
- Audit remaining public admin routes for RBAC coverage beyond connector routes.
- Wire lifecycle SQL/executor paths into production API/worker queueing and drill
  them.
- Ingest provider-native ACL snapshots from live providers and prove freshness.
- Run staging restore, rollback, load, and cost drills.
