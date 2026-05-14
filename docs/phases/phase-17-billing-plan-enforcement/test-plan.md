# Phase 17 Test Plan

- Stripe webhook signature validation.
- Webhook replay idempotency.
- Subscription state transitions.
- Trial start, active subscription, grace period, past due, canceled.
- Seat/workspace/source/index/retrieval/storage/model-call usage increments.
- API enforcement for over-limit writes and allowed reads.
- Worker enforcement for indexing/model-call limits.
- Billing admin permission checks.
- Billing portal link generation.
- Workspace isolation for usage and billing reads.
- Failed payment behavior preserves allowed features.
