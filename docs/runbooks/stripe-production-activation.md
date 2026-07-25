# Stripe Production Activation Runbook

This runbook covers the non-UI Stripe activation path for staging and production.
Do not record live secrets, customer emails, card data, or raw webhook payloads
in evidence.

## Required Configuration

Set these values through the environment or secret manager for each environment:

- `STRIPE_API_KEY`
- `STRIPE_WEBHOOK_SECRET`
- `STRIPE_PRICE_ID`
- `STRIPE_SUCCESS_URL`
- `STRIPE_CANCEL_URL`
- `STRIPE_PORTAL_RETURN_URL`

Required Cortex settings:

- `CORTEX_PUBLIC_AUTH_ENABLED=true`
- `CORTEX_STATE_BACKEND=sql`
- `DATABASE_URL`

## Smoke Flow

1. Confirm the target environment is staging unless this is the approved
   production cutover.
2. Confirm the deployed API includes `/billing/checkout`, `/billing/portal`, and
   `/billing/webhooks/stripe`.
3. Seed or identify a billing-admin membership for the workspace under test.
4. Create a checkout session with a billing-admin authenticated request.
5. Complete checkout with a Stripe test-mode payment method in staging.
6. Verify the Stripe webhook returns `200` and records exactly one provider event
   for the checkout session.
7. Create a billing portal session and verify it redirects to the expected Stripe
   hosted portal URL.
8. Replay the same webhook event and verify it is marked duplicate without
   mutating subscription state again.

Local no-secret preflight:

```bash
uv run python scripts/stripe_activation_smoke.py --static --fake-gateway
```

This validates the runbook contract, checkout/portal request shape, signature
verification, and duplicate webhook replay without contacting Stripe. It does
not replace staging or live Stripe evidence.

## Evidence To Record

Record only safe fields:

- environment,
- deploy revision,
- workspace ID,
- billing customer ID or hash,
- Stripe mode (`test` or `live`),
- checkout session ID prefix,
- webhook event ID prefix,
- local webhook processing status,
- duplicate replay status,
- portal session ID prefix,
- operator and timestamp.

Do not record:

- `STRIPE_API_KEY`,
- `STRIPE_WEBHOOK_SECRET`,
- card or payment method data,
- customer email,
- raw webhook payload.

## Rollback

1. Disable customer access to checkout links at the routing layer.
2. Keep webhook verification enabled so Stripe retries can be received safely.
3. Roll back the API image if route behavior is faulty.
4. Do not delete local billing rows. Reconcile Stripe to local state after the
   incident.
5. Record the Stripe event IDs that require manual reconciliation.
