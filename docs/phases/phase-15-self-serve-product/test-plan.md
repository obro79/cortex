# Phase 15 Test Plan

## Unit Tests

- Tenant model creation, update, lifecycle status, and validation.
- Membership role resolution.
- Invitation creation, expiration, acceptance, and replay behavior.
- Legal consent recording and lookup.
- Auth provider identity mapping to local users.
- CSRF token issuance and validation.
- Audit event actor/scope serialization.

## Integration Tests

- Signup maps provider identity to a local user.
- First workspace setup creates organization, workspace, owner membership, and
  legal consent.
- Invite acceptance creates the expected membership and active workspace.
- Workspace switching changes active context without changing permissions.
- API routes reject missing, invalid, and unauthorized workspace context.
- Worker jobs reject resources outside their workspace payload.
- Retrieval filters by workspace before returning chunks, citations, evidence
  packs, and gate results.
- Support override actions require target workspace, reason, permission, and
  audit event.

## Isolation Tests

- User in workspace A cannot fetch workspace B source objects by direct ID.
- User in workspace A cannot fetch workspace B evidence packs by direct ID.
- User in workspace A cannot trigger workspace B backfills, replays, reindexing,
  connector changes, or canonical approvals.
- Denied responses do not reveal whether the target exists in another
  workspace.
- Logs and audit records for denied access avoid private target details.

## Browser Tests

- New user signs up, accepts terms, creates workspace, and reaches connector
  setup.
- Owner invites teammate.
- Teammate accepts invite and lands in the invited workspace.
- User with multiple workspaces can switch between them.
- User with no workspace is routed to setup.
- Mutating onboarding and invite actions fail with missing or invalid CSRF.
- Logout clears active session and blocks protected pages.

## Migration Tests

- Existing development/test data is assigned to a default workspace.
- Workspace-scoped indexes support representative source health, evidence,
  retrieval, and job reads.
- Fixture reset/seed paths create tenant context.
- Migrations can run from a pre-Phase-15 database snapshot.

## Manual Validation

- Run two local workspaces through the same deployment and verify no data crosses
  in UI, API, retrieval, worker logs, or support operations.
- Inspect auth provider dashboard for expected users and sessions.
- Inspect audit events for real user IDs, workspace IDs, trace IDs, and denied
  access events.
- Verify production config defaults do not enable internal admin shortcuts.
