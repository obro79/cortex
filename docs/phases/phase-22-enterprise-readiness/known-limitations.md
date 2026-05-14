# Known Limitations

## Customer-Facing Status

Cortex is suitable for invite-only beta workspaces with guided setup. It is not yet ready for unattended enterprise self-serve rollout.

## Limitations

- Onboarding is not complete end to end through browser UI.
- Slack, GitHub, Linear, and repo-doc connector APIs have tenant/RBAC/plan
  enforcement for source listing, source selection, and backfill. Customer-facing
  setup UI is still incomplete.
- Billing has local and SQL-backed plan enforcement plus Stripe checkout, portal,
  and webhook verification boundaries. Production Stripe credentials, live
  checkout/portal smoke evidence, and customer plan-management routes are not
  complete.
- RBAC is enforced on hardened connector admin routes, but remaining public
  admin actions still need a route-by-route audit.
- Retrieval permission behavior now supports provider-native ACL snapshots for
  Slack, GitHub, and Linear protected chunks. Snapshot ingestion from live
  providers and freshness drills are not complete, so full provider ACL parity is
  not claimed.
- Data export and deletion have lifecycle job models, SQL persistence tables,
  and repository-backed executor foundations with fail-closed cleanup validation.
  Production API/worker queueing and drill evidence are not complete.
- Production operations have runbooks, but staging drill evidence is still
  required before broad launch.

## Supported Beta Positioning

- Hosted invite-only beta.
- Slack/GitHub/Linear/repo-docs data ingestion under guided setup.
- Workspace-scoped retrieval and evidence packs.
- Operator-assisted support with redacted diagnostics.
