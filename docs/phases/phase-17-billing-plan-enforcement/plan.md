# Phase 17 Plan: Billing And Plan Enforcement

## Goal

Add billing and plan limits without making the product brittle or blocking
allowed usage when a customer hits one limit.

## Scope

- Stripe customer and subscription integration.
- Invite-only or free-trial plan.
- Usage dimensions for seats, workspaces, connected sources, indexed objects,
  retrievals, storage, and model calls.
- API and worker plan-limit checks.
- Billing portal.
- Grace periods and failed-payment handling.
- Workspace/org admin billing page.

## Non-Goals

- No complex packaging experiments.
- No custom invoicing.
- No usage-based billing that requires perfect metering before beta.
- No enterprise procurement workflow.

## Architecture

```text
organization -> billing customer -> subscription -> plan entitlements
  -> usage meters -> limit decisions -> API/worker enforcement
```

Billing state is organization-scoped. Enforcement decisions should be cached
only as derived state and must be recomputable from Stripe plus local usage.

## Exit Criteria

- Customer can subscribe and update payment.
- Admin can view plan and billing portal link.
- Limit hits return clear allowed/denied behavior.
- Failed payments enter grace period before hard lockout.
- Existing data remains readable when write/index/model limits are reached.
