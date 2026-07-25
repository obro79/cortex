# Known Limitations

## Customer-Facing Status

Cortex is suitable for invite-only beta workspaces with guided setup. It is not yet ready for unattended enterprise self-serve rollout.

## Limitations

- Onboarding is not complete end to end through browser UI.
- Slack and GitHub connector setup have shared service contracts, but full
  customer-facing install and source-selection routes are not complete.
- Billing has local plan enforcement, but Stripe checkout, portal, and webhook
  verification are not complete.
- RBAC has a permission matrix, but route-level enforcement is not wired across
  every admin action.
- Retrieval permission behavior remains source-allowlist based; provider-native per-user ACL parity is not claimed.
- Data export and deletion have lifecycle job models, but repository-level execution is not complete.
- Production operations have runbooks, but staging drill evidence is still
  required before broad launch.

## Supported Beta Positioning

- Hosted invite-only beta.
- Slack/GitHub/Linear/repo-docs data ingestion under guided setup.
- Workspace-scoped retrieval and evidence packs.
- Operator-assisted support with redacted diagnostics.
