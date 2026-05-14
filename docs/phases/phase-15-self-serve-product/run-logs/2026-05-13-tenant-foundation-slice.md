# 2026-05-12 Tenant Foundation Slice

## Completed

- Added first-class tenant SQL tables and Alembic migration:
  - organizations,
  - workspaces,
  - users,
  - memberships,
  - invitations,
  - legal consents.
- Added typed tenant domain models:
  - tenant/user/membership/invitation statuses,
  - owner/admin/member roles,
  - `TenantContext`.
- Added in-memory tenant repository for local/test flows:
  - auth identity upsert,
  - first organization/workspace setup,
  - active membership context resolution,
  - admin-gated invitation creation,
  - invitation acceptance,
  - legal consent recording.
- Added local email auth adapter as the beta-default adapter boundary.
- Added config flags for public auth provider and required terms version.

## Decisions

- Phase 15 starts with workspace membership as the effective role. Separate
  organization-level roles remain deferred until enterprise RBAC.
- `local` auth is the default development/beta adapter boundary. Clerk/Auth0/
  Supabase/OIDC can plug into the same identity shape later.
- Internal admin sessions remain disabled by default through existing
  production-safe settings.

## Validation

```bash
uv run pytest tests/tenancy tests/auth/test_local_auth_provider.py tests/test_config.py
uv run ruff check src/cortex/tenancy src/cortex/auth tests/tenancy tests/auth/test_local_auth_provider.py src/cortex/config.py
```

Result: both passed.

## Remaining Phase 15 Work

- Inventory current workspace-scoped tables and entrypoints.
- Add SQL-backed tenant repository.
- Add route dependency for public session/JWT tenant resolution.
- Add onboarding UI/API flows.
- Add worker job payload enforcement.
- Add retrieval and support-operation tenant-context enforcement tests.
- Add browser coverage for signup, workspace creation, invite acceptance,
  workspace switching, CSRF failure, and logout.
