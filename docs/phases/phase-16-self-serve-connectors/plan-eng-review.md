# Phase 16 Engineering Review

## Status

Approved after Phase 15 completion.

## Architecture Lock

All provider flows should use this shared shape:

```text
setup request -> provider adapter -> connector state -> source selection
  -> audit -> backfill job -> health read model
```

Provider adapters handle provider details. Shared services own tenant scope,
permission checks, audit, redaction, idempotency, and job enqueue.

## Required Guardrails

- OAuth state must include signed workspace/session correlation.
- Callback handlers must verify membership before completing setup.
- Provider tokens must be stored only through the existing secrets boundary.
- Backfills return job IDs and never block web requests.
- Source selection changes are idempotent and audited.
- Revoke disables ingestion before removing provider access.

## Failure Modes To Test

- OAuth callback replay.
- OAuth callback for wrong workspace/session.
- Provider grants fewer scopes than expected.
- Source removed at provider after selection.
- Backfill enqueue fails after connector install.
- Reauth succeeds but source selection becomes invalid.
- Revoke fails at provider but local connector must stop ingestion.

## Implementation Sequence

1. Add shared connector setup action contract.
2. Add mocked provider callback test harness.
3. Implement Slack install/source selection.
4. Implement GitHub App install/repo selection.
5. Add connector health states and backfill progress.
6. Add reauth/revoke.
7. Add Linear/docs flows only where provider services are ready.

## Review Checklist

- [ ] OAuth state is signed and workspace-bound.
- [ ] Setup actions require workspace admin permission.
- [ ] Tokens and secrets never render.
- [ ] Source selection is audited.
- [ ] Backfills are queued with workspace scope.
- [ ] Browser smoke covers Slack and GitHub setup.
