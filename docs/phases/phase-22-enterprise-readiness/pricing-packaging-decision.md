# Pricing And Packaging Decision

## Decision

Use invite-only beta packaging until checkout, webhook, billing portal, and
customer-facing plan management are complete.

## Beta Package

- One organization.
- One workspace by default.
- Limited seats and sources through Phase 17 entitlements.
- Read access remains available when write/index/model limits are reached.
- Operator-assisted connector setup remains acceptable during invite-only beta.

## Rationale

The product needs more evidence before broad self-serve pricing:

- Stripe integration is not complete.
- Full onboarding is not complete.
- Enterprise RBAC is only partially wired into public routes.
- Data lifecycle execution needs repository-level workers.
- Production drills need staging evidence.

## Revisit Trigger

Revisit packaging after Phase 15 through Phase 21 remaining blockers are closed
and Phase 22 launch checklist is green.
