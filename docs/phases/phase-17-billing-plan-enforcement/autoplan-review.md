# Phase 17 Autoplan Review

## Verdict

Proceed with simple billing and hard-to-misuse limits. Avoid clever pricing
machinery until product usage is real.

## CEO Review

Mode: hold scope.

The point is not pricing optimization. The point is proving Cortex can be a paid
product: customers can subscribe, admins can manage payment, and the app can
enforce clear limits without breaking trust.

## Design Review

Billing UI should be boring: current plan, usage, payment status, portal link,
and clear over-limit messages. No pricing-page polish is needed inside the app.

## Engineering Review

Stripe webhook idempotency and plan-limit placement are the hard parts. Limits
must live in shared service paths so API and workers agree.

## Decision Log

- Stripe is the default billing system.
- Organization owns billing.
- Reads should remain available when write/index/model limits are exceeded.
- Grace period precedes hard lockout.

## Approval Conditions

- Webhooks are verified and idempotent.
- Plan checks run in API and worker paths.
- Over-limit responses are explicit and audited where sensitive.
