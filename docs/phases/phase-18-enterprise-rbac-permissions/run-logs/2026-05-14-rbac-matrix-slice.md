# 2026-05-14 RBAC Matrix Slice

## Completed

- Added security admin, billing admin, and viewer membership roles.
- Added a role/permission matrix covering connector setup, source selection,
  replay, reindex, re-embed, canonical approvals, billing admin, user
  management, role management, security review, and retrieval read.
- Added a risky-action approval gate for replay, reindex, re-embed, and role
  management.
- Wired connector setup/source selection authorization through the new matrix
  while preserving the existing workspace-admin compatibility path.

## Validation

```bash
uv run pytest tests/tenancy/test_rbac.py tests/tenancy/test_tenant_models.py tests/connectors/test_setup_service.py tests/security/test_admin_authorization.py
uv run ruff check src/cortex/tenancy src/cortex/connectors/setup.py tests/tenancy/test_rbac.py tests/connectors/test_setup_service.py
```

Result: both passed.

## Remaining Phase 18 Work

- Add provider permission snapshot persistence where practical.
- Wire the matrix into concrete replay/reindex/re-embed, canonical approval,
  billing, and user-management routes once those public admin routes exist.
- Add admin UI views and audit surfaces for role/permission inspection.
- Document retrieval eligibility behavior and v1 source-allowlist limitation.
