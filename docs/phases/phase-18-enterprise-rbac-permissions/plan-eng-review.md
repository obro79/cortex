# Phase 18 Engineering Review

## Status

Approved with centralized authorization guardrails.

## Required Guardrails

- One permission service owns action decisions.
- Routes, workers, and support tools call the same permission checks.
- Audit records include actor, workspace, action, target, decision, and reason.
- Provider ACL snapshots must include freshness metadata.
- Retrieval must not imply per-user filtering unless it actually enforces it.

## Failure Modes To Test

- Role has permission in UI but API denies or allows differently.
- Worker bypasses permission service.
- Support action bypasses customer RBAC.
- Stale provider permission snapshot treated as fresh.
- Retrieval result leaks from a source the actor cannot access under the chosen
  model.

## Review Checklist

- [ ] Central permission service.
- [ ] Shared API/worker/support enforcement.
- [ ] Denied audit events.
- [ ] Freshness on provider permission snapshots.
- [ ] Explicit retrieval permission contract.
