# Known Limitations

## Customer-Facing Status

Cortex is suitable for invite-only beta workspaces with guided setup. It is not yet ready for unattended enterprise self-serve rollout.

## Limitations

- Onboarding is not complete end to end through browser UI.
- Slack, GitHub, Linear, and repo-doc connector APIs have tenant/RBAC/plan
  enforcement for source listing, source selection, and backfill. Customer-facing
  setup UI is still incomplete.
- Billing has local and SQL-backed plan enforcement plus Stripe checkout, portal,
  customer-facing API routes, and webhook verification boundaries. Production
  Stripe credentials and live checkout/portal/webhook smoke evidence are not
  complete.
- RBAC is enforced on connector, billing, and lifecycle admin routes. Dev routes
  remain feature-flagged and public when explicitly enabled, so they must stay
  disabled outside local/test environments.
- Retrieval permission behavior now supports provider-native ACL snapshots for
  Slack, GitHub, and Linear protected chunks. Snapshot ingestion collectors,
  hashed user-principal mapping, and freshness reporting exist, but scheduled
  production ingestion and staging freshness drills are not complete, so full
  provider ACL parity is not claimed.
- Data export and deletion have lifecycle job models, SQL persistence tables,
  API request/status/lease/execute/retry routes, a SQL worker role, and
  repository-backed executors with fail-closed cleanup validation. Staging
  deletion/export drill evidence is not complete.
- Production operations have runbooks, but staging drill evidence is still
  required before broad launch.

## Supported Beta Positioning

- Hosted invite-only beta.
- Slack/GitHub/Linear/repo-docs data ingestion under guided setup.
- Workspace-scoped retrieval and evidence packs.
- Operator-assisted support with redacted diagnostics.
