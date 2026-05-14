# Public Route RBAC Audit

Date: 2026-05-14

Scope: backend API routes excluding `/ui/*`.

## Public By Design

| Route | Guard | Status |
| --- | --- | --- |
| `GET /health/live` | None | Public liveness endpoint. |
| `GET /health/ready` | None | Public readiness endpoint with safe config flags only. |
| `GET /case-study` | None | Public redacted artifact. |
| `POST /billing/webhooks/stripe` | Stripe signature verification | Public provider webhook. |
| `POST /connectors/slack/oauth/complete` | OAuth state | Public OAuth completion. |
| `GET /connectors/slack/oauth/callback` | OAuth state | Public OAuth callback. |
| `POST /connectors/slack/events` | Slack signature verification | Public provider webhook. |
| `POST /connectors/github/events` | GitHub HMAC verification | Public provider webhook. |

## Tenant And Permission Gated

| Route group | Permission |
| --- | --- |
| `/billing/checkout`, `/billing/portal` | `BILLING_ADMIN` |
| `/lifecycle/deletions/*`, `/lifecycle/exports/*` | `SECURITY_REVIEW` |
| `/connectors/slack/oauth/start`, `/connectors/slack/backfill/*` | `CONNECTOR_SETUP` |
| `/connectors/slack/channels`, `/connectors/slack/sources/select` | `SOURCE_SELECT` |
| `/connectors/slack/health/*` | `RETRIEVAL_READ` |
| `/connectors/github/install/*`, `/connectors/github/backfill/*` | `CONNECTOR_SETUP` |
| `/connectors/github/sources/select` | `SOURCE_SELECT` |
| `/connectors/github/health/*` | `RETRIEVAL_READ` |
| `/connectors/linear/install/*`, `/connectors/linear/backfill/*` | `CONNECTOR_SETUP` |
| `/connectors/linear/sources/select` | `SOURCE_SELECT` |
| `/connectors/linear/health/*` | `RETRIEVAL_READ` |
| `/connectors/repo-docs/import/*` | `CONNECTOR_SETUP` |
| `/connectors/repo-docs/sources/select` | `SOURCE_SELECT` |
| `/connectors/repo-docs/health/*` | `RETRIEVAL_READ` |

All tenant-gated routes use public tenant context, workspace matching, and role
permission checks before customer-scoped work.

## Dev Routes

`/dev/*` routes are public if enabled. The app factory now rejects
`CORTEX_DEV_WORKBENCH_ENABLED=true` unless `CORTEX_ENV` is `local` or `test`.
They must not be exposed in staging or production.

## Residual Review Items

- GitHub webhook signature verification is present and unselected repositories
  are ignored before ingestion; follow-up route tests should cover
  source-connection binding for incoming deliveries.
- Slack webhook tenant resolution should keep failing closed for unmapped teams;
  query fallback is acceptable only for local/test fixtures.
- Route tests cover the newly added billing and lifecycle admin routes. Any new
  public/admin route must be added to this audit and denied-role test coverage
  before launch.
