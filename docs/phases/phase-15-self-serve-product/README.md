# Phase 15: Self-Serve Product Foundation

Phase 15 starts the post-Phase-14 productization track. It defines what a
customer is, replaces internal admin shortcuts with real user identity, and
creates the onboarding path required before connector setup, billing, RBAC, and
customer-admin UI can be credible.

Phase source of truth: [`../implementation-roadmap.md`](../implementation-roadmap.md#phase-15-self-serve-product-foundation)

## Artifacts

- [Plan](plan.md)
- [Implementation checklist](implementation-checklist.md)
- [Test plan](test-plan.md)
- [Autoplan review](autoplan-review.md)
- [Engineering review](plan-eng-review.md)

## Operating Constraints

- Tenant isolation is a product boundary, not a UI filter.
- Public auth replaces internal actor headers for customer traffic.
- Every API, worker, retrieval, UI, and support action resolves a real
  workspace scope.
- Internal admin/session shortcuts stay explicitly gated and disabled by
  default in production.
- Audit events identify real users wherever a user session exists.
- Phase 15 should enable invite-only self-serve beta, not full enterprise IAM.
