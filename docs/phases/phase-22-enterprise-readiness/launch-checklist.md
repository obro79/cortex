# Enterprise Readiness Launch Checklist

## Gate Status

Current status: invite-only beta, not broad self-serve enterprise rollout.

## Required Evidence

- Tenant isolation: Phase 15 tenant identity, public tenant context, and worker
  scope run logs.
- Auth/onboarding: Phase 15 public auth context evidence; onboarding flow is
  still a launch blocker.
- Connector setup: Phase 16 shared setup service evidence; provider UI/API
  install routes are still launch blockers.
- Billing: Phase 17 plan enforcement core evidence; Stripe checkout/webhooks
  are still launch blockers.
- RBAC: Phase 18 role/permission matrix evidence; route-level wiring remains
  incomplete.
- Admin UI: Phase 19 navigation foundation evidence; several pages remain
  placeholder states.
- Compliance: Phase 20 lifecycle core evidence; actual repository deletion and
  export execution remain incomplete.
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
- Complete Slack and GitHub setup UI/API flows.
- Complete Stripe checkout, webhook verification, and billing portal.
- Wire RBAC checks into all public admin routes.
- Implement export/deletion workers against real repositories.
- Run staging restore, rollback, load, and cost drills.
