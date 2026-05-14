# Phase 18 Autoplan Review

## Verdict

Proceed, but keep the permission model explicit and boring. Enterprise RBAC is
valuable only if customers can predict outcomes and engineers can test them.

## CEO Review

Mode: hold scope.

The customer value is confidence: the wrong teammate cannot connect sources,
replay data, reindex everything, approve canonical memory, or change billing.

## Design Review

Admins need a clear roles table and action-denied states. Avoid policy-builder
UI. Make the v1 retrieval limitation visible if source-allowlist remains the
actual model.

## Engineering Review

Centralize permissions. Do not scatter role checks. Audit denied attempts.
Provider-native permission snapshots should be additive, not a silent promise of
perfect per-user ACLs.

## Decision Log

- Add role matrix before adding role UI.
- Keep v1 retrieval limitation explicit if per-user eligibility is incomplete.
- Require approval gates for risky replay/reindex/source actions.

## Approval Conditions

- Every sensitive action maps to a named permission.
- Denied actions are audited.
- Retrieval permission behavior is documented and tested.
