# Phase 10 Implementation Checklist

## 1. Permission Data Model

- Add or complete `PermissionScope`.
- Add later-ready `PermissionSnapshot`.
- Add provider identity mapping records.
- Add `AuditLog` if missing.
- Add indexes for workspace/provider/source/status lookups.

Acceptance:

- records map cleanly to Pydantic contracts,
- snapshots do not store raw sensitive provider member lists by default,
- audit records are append-only through normal service APIs.

Commit:

- `phase 10: add permission and audit models`

## 2. Central Permission Service

- Implement source allowlist lookup.
- Implement allowlist snapshot hash generation.
- Implement provider/source eligibility checks.
- Implement safe aggregate exclusion summaries.
- Add provider adapters for Slack channels, GitHub repos, Linear teams/projects,
  and docs roots.

Acceptance:

- all source types use the same enforcement semantics,
- non-allowlisted source details are not returned by the service,
- missing/ambiguous permission state fails closed.

Commit:

- `phase 10: add permission service`

## 3. Ingestion And Replay Enforcement

- Enforce allowlists in connector backfill/webhook/import acceptance.
- Enforce allowlists during raw-event replay.
- Prevent disabled/removed source scopes from creating retrievable content.
- Add allowlist removal hooks that pause ingestion and enqueue derived cleanup.

Acceptance:

- unapproved sources do not create active chunks,
- replay cannot recreate removed-source retrievable content,
- allowlist removal blocks retrieval immediately.

Commit:

- `phase 10: enforce permissions in ingestion`

## 4. Retrieval, Evidence, And Gate Enforcement

- Recheck allowlist before FTS/vector candidates.
- Recheck allowlist before relationship expansion.
- Recheck allowlist before ranking/evidence assembly.
- Sanitize evidence packs, source coverage, context gate reasons, and MCP
  outputs.

Acceptance:

- retrieval never returns non-allowlisted chunks/citations,
- context gate does not reveal hidden source names/URLs/IDs,
- source coverage reports only safe aggregate exclusions.

Commit:

- `phase 10: harden retrieval permission filtering`

## 5. Secret And Token Boundary

- Centralize secret metadata validation.
- Verify connectors store token material only through `SecretRef`.
- Add rotation/reauth/scope-drift state helpers.
- Add local-dev secret fallback guardrails.
- Add redaction tests for token/code/state/signing secrets.

Acceptance:

- no raw secret material appears in ordinary DB records,
- health/audit/API/log output uses metadata only,
- revoked/expired/scope-drift credentials mark connectors unhealthy.

Commit:

- `phase 10: harden secret boundaries`

## 6. Redaction And Debug Safety

- Centralize redaction helpers for logs/events/API/debug output.
- Audit dev workbench and retrieval inspector outputs.
- Audit connector health/source coverage outputs.
- Audit deadletter/pipeline run/error responses.
- Add review artifact scan helpers for run logs/screenshots.

Acceptance:

- redaction tests cover all known sensitive fields,
- debug tools are useful only after permission filtering,
- hidden internal IDs do not appear in user/agent-facing output.

Commit:

- `phase 10: harden debug redaction`

## 7. Audit Logging

- Add minimal admin authorization checks for security-sensitive actions.
- Create audit records for source allowlist changes.
- Create audit records for connector install/reauth/revoke.
- Create audit records for secret rotation status changes.
- Create audit records for deadletter replay, force reindex/reembed, debug
  export, and permission snapshot refresh.

Acceptance:

- allowlist changes, connector auth changes, replay/reindex/debug export, and
  permission snapshot refresh require an authorized admin actor,
- missing/disabled/non-admin actors are denied safely,
- admin/security actions have actor/resource/action/trace/result,
- denied attempts are audited,
- audit payloads do not include secrets or hidden source content,
- audit records are immutable through normal APIs.

Commit:

- `phase 10: add admin authorization and audit logging`

## 8. Security Review Run Logs

- Run focused security tests.
- Run non-allowlisted retrieval/debug drills.
- Run allowlist removal drill.
- Run token/secret scan.
- Create final security report in `run-logs/`.

Acceptance:

- report says `APPROVED_FOR_REAL_CUSTOMER_DATA` or `BLOCKED`,
- all P0/P1 findings are fixed before approval,
- residual risks are explicit.

Commit:

- `phase 10: record security review results`

## Commit Cadence

Do not make Phase 10 one security mega-commit. Use reviewable slices:

1. Data model.
2. Central permission service.
3. Ingestion/replay enforcement.
4. Retrieval/evidence/gate filtering.
5. Secret boundary hardening.
6. Debug redaction.
7. Audit logging.
8. Security review evidence.

Each commit should include focused tests for that slice. P0/P1 security fixes
found during review should land as separate fix commits, followed by recheck
evidence.
