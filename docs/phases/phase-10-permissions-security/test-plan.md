# Phase 10 Test Plan

## Commands

```bash
ruff check .
ruff format --check .
mypy src
pytest
```

Focused local loop:

```bash
pytest tests/permissions tests/security tests/retrieval tests/context_gate tests/connectors
```

## Coverage Map

```txt
Permission model
  -> permission scopes
  -> permission snapshots
  -> identity mappings
  -> audit logs

Allowlist enforcement
  -> Slack channels
  -> GitHub repos
  -> Linear teams/projects
  -> docs roots
  -> ingestion
  -> replay
  -> chunks/indexes
  -> relationships
  -> retrieval/evidence/gate
  -> debug/source coverage

Secrets
  -> SecretRef only
  -> token/code/state/signing secret redaction
  -> revoked/expired/scope drift health
  -> local-dev fallback separation

Debug safety
  -> logs/traces
  -> event payloads
  -> API responses
  -> MCP outputs
  -> dev workbench/retrieval inspector
  -> deadletters/pipeline runs

Audit
  -> admin authorization
  -> source allowlist changes
  -> connector auth changes
  -> admin repair actions
  -> debug export
  -> permission snapshot refresh
```

## Tests To Create

| Test file | Assertions |
| --- | --- |
| `tests/permissions/test_permission_scope_repository.py` | Scope records, statuses, indexes, mapper behavior. |
| `tests/permissions/test_permission_service.py` | Provider/source eligibility, fail-closed missing state, safe exclusion summaries. |
| `tests/permissions/test_permission_snapshots.py` | Snapshot metadata/freshness without raw sensitive member lists. |
| `tests/permissions/test_allowlist_removal.py` | Removal blocks retrieval immediately and enqueues derived cleanup. |
| `tests/permissions/test_ingestion_enforcement.py` | Non-allowlisted provider events/imports do not create retrievable chunks. |
| `tests/permissions/test_replay_enforcement.py` | Replay cannot recreate removed-source retrievable content. |
| `tests/retrieval/test_allowlist_hardening.py` | FTS/vector/relationship/ranking/evidence stages all filter hidden sources. |
| `tests/context_gate/test_permission_redaction.py` | Gate reasons do not reveal hidden names, URLs, snippets, IDs, or file names. |
| `tests/security/test_secret_boundaries.py` | Tokens/codes/states/signing secrets absent from DB metadata/logs/API/events/audit. |
| `tests/security/test_debug_redaction.py` | Workbench, retrieval inspector, health, deadletters, errors, source coverage are sanitized. |
| `tests/security/test_event_payload_redaction.py` | Pipeline events remain pointer-only/content-free. |
| `tests/security/test_admin_authorization.py` | Security-sensitive admin actions require authorized admin actors and deny missing/disabled/non-admin actors. |
| `tests/security/test_audit_log.py` | Admin/security actions append immutable safe audit records. |
| `tests/security/test_review_artifact_scanner.py` | Run logs/screenshots/captured outputs can be scanned for secret/content terms. |

## Golden Redaction Assertions

Non-allowlisted source details must never appear as:

```json
{
  "title": "hidden",
  "url": "hidden",
  "external_id": "hidden",
  "excerpt": "hidden",
  "chunk_id": "hidden",
  "source_object_id": "hidden",
  "source_name": "hidden",
  "file_name": "hidden"
}
```

Allowed source coverage shape:

```json
{
  "provider": "github",
  "allowlisted_source_count": 2,
  "excluded_source_count": 3,
  "excluded_source_names": null,
  "excluded_debug_ids": null
}
```

## Security Drill Matrix

| Drill | Expected behavior |
| --- | --- |
| Query matches hidden GitHub repo chunk | No candidate/evidence/debug leak. |
| Relationship points to hidden Slack thread | Relationship expansion skips/redacts hidden target. |
| Hidden docs root imported by mistake | No retrievable chunks; security finding. |
| Allowlist removed after indexing | Retrieval blocks immediately; cleanup enqueued. |
| Raw event replay after allowlist removal | Replay does not recreate retrievable content. |
| Token revoked | Connector unhealthy/reauth-required without token leak. |
| Debug endpoint error | Sanitized message with trace ID only. |
| Deadletter with provider payload | Pointer/metadata only; no content in output. |
| Non-admin allowlist removal attempt | Denied safely and audited without source/content leak. |

## Approval Threshold

Phase 10 can approve real customer data only if:

- focused security tests pass,
- retrieval/gate redaction tests pass,
- allowlist removal drill passes,
- secret scans pass,
- audit log tests pass,
- admin authorization tests pass,
- no P0/P1 security findings remain open,
- final report says `APPROVED_FOR_REAL_CUSTOMER_DATA`.

## Not Required In Phase 10

- Full enterprise SSO/RBAC,
- provider-native per-user ACL enforcement,
- public admin console,
- full deletion/retention implementation,
- Phase 11 dashboards/alerts,
- new connectors.
