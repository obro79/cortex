# Phase 15 Autoplan Review

## Verdict

Proceed, but keep Phase 15 focused on tenant, auth, and onboarding foundations.
Do not pull billing, enterprise RBAC, or a polished admin UI into this phase.

The key product bet is simple: self-serve is not real until a customer can sign
up, get a workspace, invite someone, and operate inside a tenant boundary that
cannot leak data.

## CEO Review

Mode: selective expansion.

The user-facing win is controlled beta self-serve. The smallest credible version
is not "every enterprise feature." It is a clean customer boundary:

- a real account,
- a real workspace,
- a real teammate invite,
- real route protection,
- real audit,
- no internal actor-header path for customer traffic.

Expand the phase only enough to make connector setup possible after onboarding.
Billing, advanced permissions, compliance polish, and enterprise rollout are
separate phases because each has its own failure modes.

## Design Review

Phase 15 needs product design, but not visual polish. The onboarding flow should
be short and operational:

- sign up,
- accept terms,
- create or join workspace,
- switch workspace when needed,
- invite teammate,
- continue to connector setup.

Avoid marketing pages, decorative empty states, and broad settings IA. The
design risk is confusion around "organization" versus "workspace", so the UI
must use those terms consistently and keep the active workspace visible.

## Engineering Review

This is a foundation phase. The technical center is `TenantContext`.

The right implementation shape:

- auth validates identity,
- tenancy resolves organization/workspace/user/membership,
- services require scoped context,
- repositories filter by workspace,
- workers carry workspace scope in payloads,
- retrieval filters before ranking,
- audit records actor and scope.

Main risks:

- adding auth UI without closing API/worker isolation gaps,
- treating `workspace_id` as a user-controlled parameter,
- forgetting retrieval citation expansion after the first filtered query,
- leaving internal actor headers active in production,
- creating audit events that still name only synthetic actors.

## DX Review

Local development must remain simple:

- deterministic tenant seed,
- documented auth-provider local setup,
- test helper for creating users/memberships/workspaces,
- fixture reset scoped to one workspace,
- clear config flags for public auth versus internal admin mode.

Tests should make isolation failures cheap to catch. Add factory helpers so new
phase work cannot accidentally create customer data outside a workspace.

## Decision Log

- Make Phase 15 the foundation for tenant, auth, and onboarding.
- Keep Phase 16 for self-serve connector setup.
- Keep Phase 17 for billing and plan enforcement.
- Keep Phase 18 for enterprise RBAC and permission hardening.
- Keep Phase 19 for polished customer admin UI.
- Keep Phase 20 for data lifecycle, compliance, and trust.
- Keep Phase 21 for production operations.
- Add Phase 22 as an enterprise readiness gate.
- Use owner/admin/member roles in Phase 15 and defer finer-grained roles.
- Require every customer data path to resolve tenant scope before data access.

## Approval Conditions

- Phase 15 implementation must include tenant isolation tests across API,
  workers, retrieval, UI, and support paths.
- Internal admin shortcuts must be explicitly disabled by default in production.
- New onboarding must reach connector setup without manual database edits.
- Audit events must identify real users for customer-session actions.
- No Phase 16 connector self-serve work should start until tenant context is
  mandatory across the core paths.
