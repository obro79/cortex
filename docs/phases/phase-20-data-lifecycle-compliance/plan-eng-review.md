# Phase 20 Engineering Review

## Status

Approved with deletion and derived-data guardrails.

## Required Guardrails

- Deletion jobs must be idempotent and resumable.
- Tombstones must prevent replay from resurrecting deleted data.
- Derived indexes must be cleaned or rebuilt from remaining authoritative data.
- Exports must be workspace-scoped and permission-gated.
- Audit/legal retention must be documented before user deletion behavior lands.

## Failure Modes To Test

- Raw event replay resurrects deleted source.
- Vector index still returns deleted chunk.
- Export includes another workspace's data.
- Retention sweep deletes active customer data.
- Secret rotation leaves old secret accepted.

## Review Checklist

- [ ] Workspace/source/user deletion paths.
- [ ] Tombstone/replay protection.
- [ ] Derived index cleanup.
- [ ] Export isolation.
- [ ] Secret rotation evidence.
