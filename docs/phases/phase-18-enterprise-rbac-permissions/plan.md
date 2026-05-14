# Phase 18 Plan: Enterprise RBAC And Permission Hardening

## Goal

Move beyond owner/admin/member while preserving a simple, testable permission
model for sensitive actions and retrieval.

## Scope

- Roles: owner, admin, security admin, billing admin, member, viewer.
- Fine-grained permissions for connector setup, source selection, replay,
  reindex, canonical approvals, billing, and user management.
- Provider-native permission snapshots where practical.
- Per-user retrieval eligibility model, or explicit v1 limitation if the system
  remains source-allowlist only.
- Approval gates for risky actions.

## Non-Goals

- No full SCIM/SAML lifecycle unless already needed for a customer.
- No pretending provider-native ACL parity exists before it is implemented.
- No custom policy language.

## Exit Criteria

- Sensitive actions are permissioned, audited, and denied safely.
- Admins can understand who can do what.
- Retrieval permission behavior is explicit, tested, and documented.
