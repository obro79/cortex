# 2026-05-14 Lifecycle Core Slice

## Completed

- Added lifecycle domain models for retention policy, retention sweep plan,
  deletion tombstone, export job, and lifecycle action status.
- Added in-memory lifecycle repository for local/test flows.
- Added retention policy configuration and sweep cutoff planning.
- Added deletion request tombstones with hashed target IDs.
- Added export job request and completion flow.
- Audited retention, deletion, and export lifecycle actions.

## Validation

```bash
uv run pytest tests/lifecycle/test_lifecycle_service.py
uv run ruff check src/cortex/lifecycle tests/lifecycle/test_lifecycle_service.py
```

Result: both passed.

## Remaining Phase 20 Work

- Wire workspace/source/user deletion workflows into actual data repositories.
- Add SQL persistence and migrations for lifecycle jobs and tombstones.
- Add derived index cleanup/rebuild, secret rotation procedures, privacy docs,
  control mapping, incident runbook, and abuse controls.
