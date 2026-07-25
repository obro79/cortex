# 2026-05-13 Public Auth Context Slice

## Completed

- Added a FastAPI tenant-context dependency for public-auth API routes.
- Resolved active organization, workspace, user, membership role, session ID,
  and trace ID through the tenant repository.
- Rejected missing public auth, missing workspace/auth headers, cross-workspace
  membership access, and internal actor headers on public-auth traffic.
- Provisioned an in-memory tenant repository when public auth is enabled so the
  app has an explicit tenant boundary during local/beta development.

## Validation

```bash
uv run pytest tests/auth tests/tenancy tests/test_config.py
uv run ruff check src/cortex/auth src/cortex/api/app.py tests/auth tests/tenancy
```

Result: both passed.

## Remaining Phase 15 Work

- Replace the in-memory public-auth repository with SQL-backed tenant
  persistence for production state backends.
- Add onboarding routes and UI flows for organization/workspace creation,
  legal consent, invites, invite acceptance, workspace switching, logout, and
  empty-state routing.
- Add worker, retrieval, support-operation, audit, CSRF, and browser coverage.
