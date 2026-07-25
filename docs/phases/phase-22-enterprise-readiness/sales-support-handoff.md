# Sales And Support Handoff

## Sellable Scope

- Invite-only hosted beta for teams willing to work through guided setup.
- Workspace-scoped ingestion and retrieval across supported source types.
- Evidence packs and source health visibility where implemented.
- Redacted support diagnostics and audit-backed sensitive actions.

## Do Not Promise

- SOC 2 certification.
- Enterprise SAML/SCIM.
- Provider-native per-user ACL parity.
- Fully unattended self-serve setup.
- Custom invoicing or procurement workflow.
- Guaranteed deletion from upstream provider systems.

## Support Intake Requirements

- Organization ID.
- Workspace ID.
- Actor ID when available.
- Trace ID.
- Approximate timestamp.
- Provider and source type.
- Error code or status.

Never request provider tokens, session tokens, raw private messages, raw
documents, or private file URLs in support intake.

## Escalation

- Security issue: security owner plus incident runbook.
- Data isolation concern: tenant isolation evidence and audit review.
- Billing concern: billing owner and current plan entitlement state.
- Connector failure: connector setup state, backfill status, and provider error
  code only.
