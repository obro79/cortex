# Phase 10 Plan: Permissions And Security

## Goal

Harden Cortex after all v1 sources exist:

```txt
connected sources
  -> source allowlists
  -> permission snapshots/checks
  -> retrieval/debug redaction
  -> secret/token boundary
  -> audited admin actions
  -> security review gate
```

Phase 10 is not a new connector phase. It turns the Slack/Linear/GitHub/docs
system into something credible for production team usage by proving
non-allowlisted content and secrets cannot leak through retrieval, logs, traces,
events, health, debug tools, source coverage, or run artifacts.

## Inputs

- [`../implementation-roadmap.md`](../implementation-roadmap.md#phase-10-permissions-and-security)
- [`../../architecture/handbook.md`](../../architecture/handbook.md)
- [`../../architecture/v1-entity-state-schema.md`](../../architecture/v1-entity-state-schema.md)
- [`../../architecture/pipeline-event-envelope.md`](../../architecture/pipeline-event-envelope.md)
- [`../../architecture/adrs/009-source-allowlist-permissions-v1/README.md`](../../architecture/adrs/009-source-allowlist-permissions-v1/README.md)
- [`../../architecture/adrs/012-secrets-token-management/README.md`](../../architecture/adrs/012-secrets-token-management/README.md)
- [`../../architecture/adrs/013-webhook-security-idempotency/README.md`](../../architecture/adrs/013-webhook-security-idempotency/README.md)
- [`../phase-05-retrieval-evidence-packs/plan.md`](../phase-05-retrieval-evidence-packs/plan.md)
- [`../phase-08-5-slack-review-manual-testing/plan.md`](../phase-08-5-slack-review-manual-testing/plan.md)
- [`../phase-09-linear-github-repo-docs/plan.md`](../phase-09-linear-github-repo-docs/plan.md)

## Existing Foundation

Earlier phases provide:

- source connections for Slack, Linear, GitHub, and repo docs,
- v1 source allowlist assumptions,
- retrieval permission filtering and source coverage,
- evidence packs and context gate outputs,
- secret refs for OAuth/provider tokens,
- webhook verification/idempotency patterns,
- run logs from Phase 8.5 manual review,
- redaction rules in event envelope docs and connector plans.

Phase 10 should centralize and enforce those rules instead of leaving them as
provider-by-provider conventions.

## Non-Goals

- No full enterprise SSO/RBAC product.
- No full provider-native per-user ACL enforcement in retrieval.
- No public admin console.
- No deletion/retention workflow beyond planning hooks and permission-safe
  allowlist removal behavior.
- No new source connectors.
- No broad observability dashboard work; Phase 11 owns dashboards and alerts.

## Architecture

```txt
PermissionService
  -> source allowlist scopes
  -> permission snapshot records
  -> retrieval/debug eligibility checks
  -> allowlist removal/deindex hooks

SecretBoundaryService
  -> SecretRef metadata validation
  -> secret redaction checks
  -> rotation/reauth status
  -> local-dev secret-store separation

RedactionService
  -> logs/events/API/debug/evidence/source-coverage sanitizers
  -> denylisted fields and content-like value detection
  -> review artifact scanning helpers

AuditService
  -> admin action audit
  -> connector/security action audit
  -> approval/security event cross references

AdminAuthorizationService
  -> minimal admin actor checks
  -> permission-gated security/admin actions
  -> safe denial responses

IdentityMappingService
  -> later-ready provider identity links
  -> Slack/Linear/GitHub external users
  -> no retrieval enforcement from identity map in Phase 10
```

The core rule: source allowlist checks happen before ingestion, indexing,
retrieval ranking, evidence building, relationship expansion, debug output, and
source coverage rendering.

## Proposed Module Layout

```txt
src/cortex/security/
  __init__.py
  admin_auth.py
  redaction.py
  audit.py
  secrets.py
  debug_safety.py

src/cortex/permissions/
  __init__.py
  scopes.py
  snapshots.py
  service.py
  filters.py
  removal.py
  identity.py

tests/security/
tests/permissions/
```

Reuse provider connector modules for provider-specific scope and secret
metadata. Central services should decide safety, not duplicate provider API
logic.

## Data Model

Complete or add records for:

- `permission_scopes`,
- `permission_snapshots`,
- `audit_logs`,
- provider identity mapping records if not already present,
- secret rotation/reauth metadata where missing.

`PermissionScope` is the active v1 enforcement primitive:

- Slack channel,
- GitHub repository,
- Linear team/project,
- repo docs root.

`PermissionSnapshot` is later-ready metadata:

- provider,
- source scope,
- snapshot version,
- captured_at,
- freshness/status,
- hash of provider permission state,
- safe non-content counts,
- no raw member lists in v1.

`AuditLog` should be append-only for admin/security actions:

- source allowlist add/remove,
- connector install/reauth/revoke,
- token rotation state change,
- deadletter replay,
- force reindex/reembed,
- debug export,
- deletion/retention repair trigger,
- permission snapshot refresh.

## Minimal Admin Authorization

Phase 10 does not need full enterprise RBAC, but it must require an authorized
admin actor for security-sensitive actions.

Permission-gated actions:

- source allowlist add/remove,
- connector install, reauth, revoke, and disable,
- token rotation state changes,
- deadletter replay,
- force reindex/reembed,
- debug export or raw diagnostic bundle generation,
- deletion/retention repair trigger,
- permission snapshot refresh.

Minimum v1 actor model:

- require `workspace_id`,
- require `actor_id`,
- require actor role/capability such as `workspace_admin` or
  `security_admin`,
- deny missing, unknown, disabled, or non-admin actors,
- log both allowed and denied attempts without secrets or hidden source content.

This is intentionally smaller than full RBAC, but audit without authorization is
not sufficient for Phase 10.

## Source Allowlist Enforcement

Enforce allowlists at every boundary:

1. Connector source selection.
2. Backfill/webhook/import acceptance.
3. Raw-event replay.
4. Source object/chunk creation.
5. Relationship building.
6. FTS/vector candidate generation.
7. Ranking and evidence-pack assembly.
8. Context gate reason rendering.
9. Debug/dev workbench/source coverage output.
10. Admin/health endpoints.

Non-allowlisted content must not expose:

- title,
- URL,
- external ID,
- excerpt/snippet,
- chunk ID,
- source object ID,
- source name,
- file name,
- private repo/channel/team/project/docs path,
- debug IDs that can be joined back to hidden records.

Source coverage may report safe aggregate counts such as
`excluded_source_count` or `excluded_provider_count` without names or IDs.

## Allowlist Removal

Allowlist removal should:

- stop future ingestion for the source,
- mark source connection disabled/removed,
- stop retrieval eligibility immediately,
- enqueue deindex/delete of chunks, embeddings, and derived index entries,
- preserve non-content audit/tombstone metadata where needed,
- prevent replay from recreating retrievable content for removed scopes.

Full deletion workflows can deepen later, but retrieval must fail closed
immediately after removal.

## Secret And Token Boundary

Enforce:

- no raw token material in ordinary DB tables,
- no token/code/state/signing secret in logs, traces, events, audit payloads, or
  API responses,
- connector health uses secret metadata only,
- revoked/expired/scope-drift tokens mark connectors unhealthy or
  reauth-required,
- rotation preserves source connection identity,
- local-dev secret fallback is visibly separated from production secret store.

Secret scans must include Phase 8/9 run logs and screenshots before committing
review artifacts.

## Debug Output Audit

Audit and harden:

- dev workbench,
- retrieval inspector,
- evidence-pack viewer,
- source coverage,
- connector health,
- deadletter views,
- pipeline run views,
- logs and traces,
- event payloads,
- error responses,
- MCP tool outputs.

Debug output should be useful only after permission filtering. Internal raw IDs
for hidden sources should not appear in agent-facing or user-facing output.

## Identity Mapping

Add later-ready provider identity mapping across Slack, Linear, and GitHub:

- provider,
- external user ID hash or protected reference,
- display-name/email hash where needed,
- workspace actor link when known,
- status and freshness.

Phase 10 should not use this as a full ACL enforcement layer. It exists to make
future provider-native permission snapshots possible and to reduce ambiguity in
audit/approval flows.

## Security Review Gate

Before claiming Phase 10 complete, produce a run log with:

- security test commands,
- redaction scan results,
- allowlist removal drill,
- non-allowlisted retrieval/debug drill,
- token/secret boundary checks,
- audit log checks,
- residual risks,
- final decision: `APPROVED_FOR_REAL_CUSTOMER_DATA` or `BLOCKED`.

## Acceptance Criteria

Phase 10 is complete when:

- all source types enforce allowlists consistently,
- retrieval only returns allowlisted chunks/citations,
- debug/source coverage/health/deadletter outputs do not leak hidden source
  identifiers or content,
- allowlist removal immediately blocks retrieval and schedules derived cleanup,
- tokens/secrets never appear in DB metadata, logs, events, API responses, audit
  payloads, or run artifacts,
- admin/security actions create audit records,
- security-sensitive admin actions require an authorized admin actor before they
  execute,
- later-ready identity and permission snapshot models exist without pretending
  to enforce full provider-native ACLs,
- security review report approves use with real customer data or blocks with
  concrete fixes.
