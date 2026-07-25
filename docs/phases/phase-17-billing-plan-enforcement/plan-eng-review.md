# Phase 17 Engineering Review

## Status

Approved with Stripe/idempotency guardrails.

## Required Guardrails

- Verify Stripe webhook signatures.
- Store processed webhook event IDs.
- Treat Stripe as billing source of truth and local state as synchronized
  projection.
- Put enforcement in shared entitlement service.
- Avoid hard-deleting or hiding customer data because payment failed.
- Keep read-only access available unless a later policy explicitly says
  otherwise.

## Failure Modes To Test

- Duplicate webhook.
- Out-of-order webhook.
- Subscription downgraded below current usage.
- Usage meter increment race.
- Worker starts expensive job after plan limit is reached.
- Billing portal requested by non-billing admin.

## Review Checklist

- [ ] Webhook idempotency.
- [ ] Shared entitlement service.
- [ ] API and worker enforcement.
- [ ] Grace period behavior.
- [ ] No data visibility loss from billing failure.
