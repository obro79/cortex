# Phase 15 Plan: Self-Serve Product Foundation

## Goal

Define the customer boundary and build the tenant, auth, and onboarding spine
needed for controlled self-serve beta.

Phase 15 is successful when a new user can sign up, create a workspace, invite a
teammate, switch workspace context, and reach connector setup without manual
database edits, while every existing data path remains workspace-scoped.

## Inputs

- [`../implementation-roadmap.md`](../implementation-roadmap.md#self-serve-productization-track)
- [`../phase-10-permissions-security/plan.md`](../phase-10-permissions-security/plan.md)
- [`../phase-11-observability-operations/plan.md`](../phase-11-observability-operations/plan.md)
- [`../phase-13-layer-later-platform/plan.md`](../phase-13-layer-later-platform/plan.md)
- [`../phase-14-minimal-web-ui/plan.md`](../phase-14-minimal-web-ui/plan.md)
- [`../../architecture/v1-entity-state-schema.md`](../../architecture/v1-entity-state-schema.md)
- [`../../architecture/adrs/014-retention-deletion/README.md`](../../architecture/adrs/014-retention-deletion/README.md)

## Non-Goals

- Do not build paid billing in Phase 15.
- Do not build enterprise SAML/SCIM.
- Do not implement per-user provider-native retrieval ACLs unless existing
  Phase 10 work already supports them.
- Do not polish the full customer admin UI beyond onboarding and workspace
  context.
- Do not support arbitrary multi-region or data-residency controls.
- Do not keep internal admin headers as a customer-facing auth path.

## Product Boundary

Introduce the customer hierarchy:

```text
Organization
  |
  +-- Workspace
        |
        +-- Membership
              |
              +-- User
```

Definitions:

- Organization: billing, legal, and top-level customer account boundary.
- Workspace: operational data boundary for sources, retrieval, jobs, decisions,
  evidence packs, and support actions.
- User: authenticated human identity from the auth provider.
- Membership: user access to an organization/workspace with role and status.
- Role: owner, admin, or member for Phase 15.

Phase 15 should preserve the current `workspace_id`-centered data model where it
already exists, but make workspace resolution explicit and mandatory.

## Architecture

```text
Browser/API client
  |
  v
Auth provider session/JWT
  |
  v
Auth boundary
  |
  +--> User identity
  +--> Organization membership
  +--> Workspace membership
  +--> Active workspace context
  |
  v
Tenant-scoped services
  |
  +--> APIs
  +--> UI routes
  +--> workers/jobs
  +--> retrieval/evidence
  +--> canonical memory
  +--> support operations
  +--> audit log
```

Recommended module boundaries:

```text
src/cortex/auth/
  provider.py
  sessions.py
  csrf.py
  dependencies.py

src/cortex/tenancy/
  models.py
  repositories.py
  context.py
  isolation.py
  onboarding.py
  invites.py

src/cortex/audit/
  actor.py
  events.py
```

The exact paths should follow the implementation shape that exists when Phase
15 starts, but the boundaries should stay intact: auth validates identity,
tenancy resolves scope, services operate only after scope is known, and audit
records the actor/scope/action/result.

## Data Model

Add or formalize:

- `organizations`
- `workspaces`
- `users`
- `memberships`
- `workspace_memberships` if organization and workspace roles diverge
- `invitations`
- `legal_consents`
- `sessions` or provider-session mapping if needed
- `audit_events` actor fields for real users

Required fields:

- stable internal ID,
- external auth provider ID where applicable,
- display name/email where allowed,
- lifecycle status,
- timestamps,
- created-by actor,
- workspace or organization foreign keys as appropriate.

Every existing table that stores customer data must either have `workspace_id`
or a documented derivation from a workspace-scoped parent. Derived indexes must
be rebuildable per workspace.

## Tenant Isolation Contract

Every request or job must resolve `TenantContext` before touching customer data.

`TenantContext` should include:

- organization ID,
- workspace ID,
- actor user ID when interactive,
- membership role and permissions,
- session ID when interactive,
- trace ID,
- support/admin override metadata when applicable.

Isolation rules:

- API handlers must not accept arbitrary `workspace_id` without membership
  verification.
- Worker jobs must carry workspace ID and validate the referenced resources
  belong to that workspace before acting.
- Retrieval queries must filter by workspace before ranking, chunk loading, or
  citation expansion.
- UI routes must use active workspace context from verified membership.
- Support actions must require explicit target workspace and audit reason.
- Audit logs must capture denied actions as well as allowed actions.

## Auth And Session Contract

Pick one auth provider for beta and build behind an adapter. Clerk, Auth0,
Supabase Auth, or custom OIDC are acceptable if the integration can support:

- email login,
- Google or GitHub SSO,
- verified email status,
- logout,
- session validation for UI and APIs,
- webhook or sync path for user changes where needed.

Customer traffic must use provider-backed sessions/JWTs. Internal admin headers
may exist only behind a separate explicit flag and must never be enabled by
production environment defaults.

Mutating browser actions require CSRF protection tied to the authenticated
session.

## Onboarding Flow

Minimum flow:

1. User signs up or logs in.
2. User accepts required legal terms.
3. User creates first organization and workspace, or accepts an invitation.
4. User lands in active workspace context.
5. User can invite a teammate.
6. User reaches connector setup with no manual database edits.

Workspace switching should be visible and auditable. A user with no active
workspace should be routed back to setup, not into an empty broken app shell.

## Migration Path

Before adding public auth, inventory all current workspace assumptions:

- tables with `workspace_id`,
- tables missing workspace scope,
- route dependencies,
- worker payloads,
- retrieval filters,
- UI links/forms,
- support/admin paths,
- tests and fixtures.

Then migrate in order:

1. Add tenant models and seed/migration defaults for existing development data.
2. Introduce `TenantContext` dependency and job payload contract.
3. Make workspace scope mandatory in API, UI, retrieval, worker, and support
   entrypoints.
4. Add public auth and map sessions to users/memberships.
5. Replace internal actor headers in customer paths.
6. Add onboarding and invite flows.
7. Turn internal shortcuts off by default in production config.

## Security Requirements

- No cross-workspace object IDs should resolve by direct URL/API access.
- Denied routes should not reveal whether a resource exists in another
  workspace.
- Invitations must expire and be single-use or otherwise safely idempotent.
- Role changes, invites, legal consent, workspace switching, and support
  overrides must be audited.
- Account deletion hooks must either delete or deactivate user identity and
  preserve required audit/legal records according to retention policy.
- Logs and traces must include workspace/user IDs but not session tokens,
  provider tokens, or private content.

## Exit Criteria

- Two workspaces can use the same deployment without data crossing.
- Every API, worker, retrieval, UI, and support action is workspace-scoped.
- A new user can sign up, create a workspace, invite a teammate, and reach
  connector setup without manual database edits.
- Internal admin shortcuts are disabled by default in production.
