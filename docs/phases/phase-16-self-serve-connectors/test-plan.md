# Phase 16 Test Plan

## Unit Tests

- Provider setup adapter status normalization.
- Source selection validation.
- Scope/data-read explanation rendering.
- Reauth and revoke result mapping.
- Audit event generation for setup actions.

## Integration Tests

- Slack install callback creates workspace-scoped connector state.
- GitHub install callback creates workspace-scoped connector state.
- Source selection enqueues backfill with workspace ID.
- Reauth updates connector status without losing source selections.
- Revoke disables connector and blocks future ingestion.
- Backfill retry returns a job reference.

## Security Tests

- Non-admin users cannot install, select sources, reauth, revoke, or retry.
- Workspace A cannot view or change Workspace B connector state.
- OAuth tokens and provider secrets never render in HTML, API responses, logs,
  or audit details.
- Denied direct-ID access does not reveal connector existence.

## Browser Tests

- Admin connects Slack through mocked provider callback.
- Admin connects GitHub through mocked provider callback.
- Admin selects sources and sees backfill progress.
- Admin sees stale/failed/revoked connector health states.
- Member sees read-only or denied state.
