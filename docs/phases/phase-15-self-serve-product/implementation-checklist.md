# Phase 15 Implementation Checklist

## Prerequisites

- [ ] Inventory all current tables and services that store or derive customer
      data.
- [ ] Inventory all route, worker, retrieval, UI, and support entrypoints that
      currently accept or infer `workspace_id`.
- [x] Choose the beta auth provider and document why it was selected.
- [x] Decide whether organization and workspace roles are separate in Phase 15
      or whether workspace membership owns the effective role.
- [x] Define production-safe defaults for internal admin/session shortcuts.

## Tenant Models

- [x] Add organization model and migration.
- [x] Add workspace model and migration.
- [x] Add user model and migration.
- [x] Add membership model and migration.
- [x] Add invitation model and migration.
- [x] Add legal consent model and migration.
- [x] Add owner, admin, and member role definitions.
- [x] Add lifecycle statuses for organizations, workspaces, users,
      memberships, and invitations.
- [x] Add repositories/services for tenant model reads and writes.
- [ ] Add seed data for local development and tests.

## Tenant Context And Isolation

- [x] Add `TenantContext` or equivalent scoped context object.
- [x] Add route dependency for resolving active organization/workspace/user.
- [x] Add worker job payload contract requiring workspace scope.
- [ ] Add retrieval scope filter before ranking and citation expansion.
- [ ] Add UI workspace context resolver.
- [ ] Add support/admin workspace override contract with reason and audit.
- [ ] Update APIs to reject missing or unauthorized workspace context.
- [x] Update workers to validate resource ownership before acting.
- [ ] Update evidence pack, canonical memory, source object, chunk, connector,
      job, and audit reads to enforce workspace scope.
- [ ] Add tests proving direct cross-workspace ID access is denied.

## Workspace Migration

- [ ] List tables that already carry `workspace_id`.
- [ ] List tables that need direct `workspace_id`.
- [ ] List tables that can derive workspace scope through a parent record.
- [ ] Add missing workspace foreign keys or documented derivation paths.
- [ ] Backfill existing development/test data into a default workspace.
- [ ] Add indexes needed for workspace-scoped reads.
- [ ] Update fixtures and factories to create organization/workspace/user
      context.
- [ ] Add migration rollback notes.

## Public Auth

- [x] Add auth provider adapter.
- [x] Add email login support.
- [ ] Add Google or GitHub SSO support.
- [ ] Add session validation for UI routes.
- [x] Add token/session validation for API routes.
- [ ] Map provider identities to local users.
- [ ] Handle verified and unverified email states.
- [ ] Add logout.
- [ ] Add account deletion/deactivation hook.
- [ ] Add CSRF protection for browser mutations.
- [x] Disable customer access through internal actor headers.
- [ ] Keep internal admin shortcut behind an explicit non-production-safe flag.

## Onboarding

- [ ] Add first organization creation flow.
- [ ] Add first workspace creation flow.
- [ ] Add required legal consent/terms gate.
- [ ] Add active workspace selection.
- [ ] Add workspace switching.
- [ ] Add invite creation flow.
- [ ] Add invite acceptance flow.
- [ ] Add invite expiration and replay handling.
- [ ] Add empty-state routing for users with no workspace.
- [ ] Route successful onboarding to connector setup.

## Roles And Audit

- [ ] Enforce owner/admin/member permissions for invite and workspace actions.
- [ ] Audit signup, login where appropriate, workspace creation, workspace
      switch, invite create, invite accept, role change, legal consent, logout,
      denied access, and support override.
- [ ] Tie interactive audit events to real user IDs.
- [ ] Preserve trace ID and session ID on audit events where available.
- [ ] Ensure denied audit events do not leak cross-workspace resource details.

## Closeout

- [x] Add unit tests for tenant repositories and membership resolution.
- [x] Add API tests for authorized, unauthorized, and cross-workspace access.
- [x] Add worker tests for workspace-scoped jobs.
- [ ] Add retrieval isolation tests.
- [ ] Add onboarding browser tests.
- [ ] Add invite flow tests.
- [ ] Add CSRF tests for mutating browser actions.
- [ ] Add audit tests for allowed and denied actions.
- [ ] Update docs with auth provider setup and local development flow.
- [ ] Record residual limitations before Phase 16 starts.
