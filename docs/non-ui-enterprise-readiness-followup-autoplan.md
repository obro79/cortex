<!-- /autoplan follow-up generated from deep review findings on 2026-05-14 -->

# Non-UI Enterprise Readiness Follow-Up Autoplan

Status: reviewed implementation plan
Base branch: `main`
UI scope: no
DX scope: yes, operator/API/docs only
Generated: 2026-05-14

## Goal

Close the blockers found in the deep review without expanding into customer admin
UI work. The standard suite is green, but targeted lifecycle probes exposed real
compliance gaps that must be fixed before deletion/export can be trusted.

## Inputs

- `uv run pytest`: 385 passed.
- `uv run ruff check .`: passed.
- `uv run ruff format --check .`: passed.
- `uv run mypy src`: passed.
- `docker compose config`: passed.
- `uv run alembic heads`: one head, `0013_lifecycle_persistence`.
- `uv run alembic upgrade head --sql`: rendered successfully.
- Targeted probe failed: `LifecycleService` returns unawaited coroutines when used
  with `SqlAlchemyLifecycleRepository`.
- Targeted probe failed: deleting a source connection with both file-backed and
  object-level chunks leaves the object-level chunk active.

## Autoplan Result

Proceed as five backend/ops slices:

1. Lifecycle correctness: async SQL service boundary, complete chunk selection,
   and fail-closed deletion counts.
2. Lifecycle production execution: API/worker wiring, SQL executors, export
   manifests, and repairable failures.
3. Durable billing: SQL-backed billing state first, then Stripe checkout, portal,
   and webhook idempotency.
4. Provider ACL snapshots: per-user provider eligibility in retrieval, with
   fail-closed stale or missing snapshot behavior.
5. Evidence and docs: staging drills plus readiness docs that track only proven
   behavior.

The split matters. Lifecycle correctness is a P1 because the current foundation
can report compliance success while leaving data active. Billing and ACL work are
still launch blockers, but they should not block the lifecycle repair.

## Not In Scope

- Customer admin UI, onboarding UI polish, visual QA, or browser flow completion.
- SSO/SCIM enterprise identity.
- Live provider authorization checks on every retrieval request.
- Production destructive drills against real customer data.

## Decision Audit Trail

| # | Decision | Classification | Principle | Rationale |
|---:|---|---|---|---|
| 1 | Fix lifecycle correctness before adding more compliance surface. | Mechanical | Completeness | The current executor can leave active data behind, so production wiring would amplify the flaw. |
| 2 | Convert lifecycle service access to one async repository contract. | Taste | Explicit over clever | SQL repositories are async already; sync wrappers would hide await bugs and split behavior. |
| 3 | Treat lifecycle selection by object IDs and file IDs as a union. | Mechanical | Completeness | Deleting a source object must delete all chunks under it, including object-level chunks. |
| 4 | Fail tombstones on vector or payload mismatch by default. | Mechanical | Fail closed | A completed compliance job with skipped refs is worse than a failed retryable job. |
| 5 | Build SQL billing before Stripe webhooks. | Mechanical | DRY | Stripe should synchronize durable local state, not mutate in-memory enforcement. |
| 6 | Use provider ACL snapshots rather than live provider checks per retrieval. | Taste | Pragmatic | Snapshots are auditable, fast, and survive provider outages if freshness is enforced. |
| 7 | Record drill evidence only after the target control exists. | Mechanical | Evidence over claims | Running restore/load drills before lifecycle and billing paths are durable proves the wrong system. |

## Workstream 1: Lifecycle Correctness

### Problem

`SqlAlchemyLifecycleRepository` exposes async methods, while `LifecycleService`
calls them synchronously. The service returns coroutine objects instead of saved
models. Separately, lifecycle chunk filtering intersects source object IDs and
source file IDs, so object-level chunks can stay active under a deleted source
object. Finally, vector and payload cleanup mismatches are counted but do not fail
the tombstone.

### Implementation Plan

- Define one async lifecycle repository protocol and make `LifecycleService`
  methods async.
- Convert `InMemoryLifecycleRepository` methods to async or add a thin async
  adapter used by tests.
- Update lifecycle tests to await service calls.
- Change lifecycle chunk selection to union records matched by source object IDs,
  source file IDs, or explicit chunk IDs.
- Apply the same union semantics to SQL and in-memory chunk repositories.
- Add a deletion result validator that compares expected refs to deleted refs.
- Mark tombstones `failed` when vector points, payload refs, chunks, embeddings, or
  index jobs do not match expected cleanup.
- Preserve per-store counts in tombstone metadata for repair and audit.

### Primary Files

- `src/cortex/lifecycle/service.py`
- `src/cortex/lifecycle/executors.py`
- `src/cortex/chunking/repositories.py`
- `src/cortex/embeddings/repositories.py`
- `src/cortex/indexing/repositories.py`
- `src/cortex/ingestion/payloads.py`
- `tests/lifecycle/test_lifecycle_service.py`

### Tests

- Add regression test for async SQL repository use through lifecycle service.
- Add regression test for deleting mixed object-level and file-level chunks.
- Add tests for vector point missing, payload ref missing, and missing deleter
  failing the tombstone.
- Keep happy-path deletion/export manifest tests.

### Acceptance Gate

- The two targeted probes from the deep review become committed tests and pass.
- A completed tombstone means all expected stores were cleaned or explicitly
  recorded as allowed omissions.

## Workstream 2: Lifecycle Production Execution

### Problem

Lifecycle persistence and local executors exist, but production request/worker
wiring is not complete. Export is also still local-store oriented and does not
prove payload/file coverage for real SQL state.

### Implementation Plan

- Add security-admin protected API endpoints for deletion requests, deletion job
  status, export requests, and export job status.
- Wire SQL lifecycle repository and SQL deletion/export executors through the app
  factory when `CORTEX_STATE_BACKEND=sql`.
- Add worker entrypoints that lease requested deletion/export jobs and transition
  them through requested, running, completed, and failed states.
- Implement SQL-backed lifecycle executors using batch queries by workspace and
  target type.
- Add a vector deleter backed by the production vector index interface.
- Extend export manifests with store counts, payload refs, skipped refs, hashes,
  created timestamp, and workspace ID.
- Ensure retrieval, FTS, vector, and source listing paths exclude deleted data.
- Add repair docs for failed lifecycle tombstones.

### Primary Files

- `src/cortex/api/app.py`
- `src/cortex/auth/dependencies.py`
- `src/cortex/lifecycle/service.py`
- `src/cortex/lifecycle/executors.py`
- `src/cortex/workers/main.py`
- `src/cortex/workers/factory.py`
- `src/cortex/db/models.py`
- `docs/runbooks/`

### Tests

- Route tests for security-admin access and viewer/member denial.
- SQL integration tests for source connection, source object, source file,
  source chunk, raw event, embedding, and workspace deletion.
- Export manifest integration test with raw events, files, chunks, embeddings,
  and skipped refs.
- Retrieval-after-deletion tests for FTS and vector paths.

### Acceptance Gate

- A SQL-backed deletion/export job can be requested, executed by a worker, audited,
  and inspected without using in-memory repositories.

## Workstream 3: Durable Billing And Stripe

### Problem

`PlanEnforcementService` is wired to `InMemoryBillingRepository` in the app
factory. That is adequate for local tests, but a restart loses customers,
subscriptions, and usage. Stripe integration cannot be trusted until local state
is durable and idempotent.

### Implementation Plan

- Add billing tables for customers, subscriptions, usage meters, entitlement
  snapshots, and provider webhook events.
- Implement `SqlAlchemyBillingRepository` with the same public contract as the
  in-memory repository.
- Wire SQL billing enforcement when `CORTEX_STATE_BACKEND=sql`.
- Keep in-memory billing for unit tests and explicit memory-mode app instances.
- Add a Stripe gateway abstraction for checkout session creation, billing portal
  creation, webhook signature verification, and subscription state mapping.
- Persist Stripe event IDs before processing side effects.
- Handle duplicate and out-of-order webhook events idempotently. Idempotent means
  repeated provider events have one durable effect, not repeated usage or plan
  changes.
- Add reconciliation command or worker hook to compare Stripe subscription state
  against local durable records.

### Primary Files

- `src/cortex/billing/models.py`
- `src/cortex/billing/service.py`
- `src/cortex/api/app.py`
- `src/cortex/auth/dependencies.py`
- `src/cortex/db/models.py`
- `alembic/versions/`
- `tests/billing/`

### Tests

- Repository contract tests run against in-memory and SQL billing repositories.
- Route tests prove source selection and backfill enforcement use SQL usage state.
- Stripe webhook tests cover missing signature, invalid signature, duplicate event,
  out-of-order subscription update, cancellation, trialing, active, and past due.
- Checkout and portal tests use a fake Stripe gateway.

### Acceptance Gate

- Public connector enforcement survives app restart under SQL state.
- Stripe webhook replay does not double count usage or flap entitlements.

## Workstream 4: Provider ACL Snapshots

### Problem

Retrieval currently relies on workspace scope, permission scopes, and source
allowlists. That is not provider-native per-user authorization. Enterprise claims
need a snapshot of which provider principals can access which provider resources,
without storing raw external IDs in diagnostics.

### Implementation Plan

- Add provider ACL snapshot and ACL entry tables.
- Store hashed provider principal IDs and hashed provider resource IDs.
- Add freshness metadata: provider, source connection, captured time, expires time,
  snapshot hash, and stale reason.
- Add provider-specific resource mappers for Slack channels, GitHub repositories,
  Linear teams/projects, and repo-doc roots.
- Extend retrieval input to include caller principal context.
- Extend `PermissionService.check_chunk()` to require provider ACL eligibility for
  protected chunks.
- Fail closed when a protected chunk has no current snapshot, stale snapshot, or
  ambiguous mapping.
- Store ACL snapshot hash and permission exclusions on retrieval requests and
  evidence packs.

### Primary Files

- `src/cortex/permissions/scopes.py`
- `src/cortex/permissions/service.py`
- `src/cortex/retrieval/service.py`
- `src/cortex/retrieval/permissions.py`
- `src/cortex/connectors/slack/`
- `src/cortex/connectors/github/`
- `src/cortex/connectors/linear/`
- `src/cortex/connectors/repo_docs/`
- `src/cortex/db/models.py`
- `alembic/versions/`

### Tests

- Snapshot builder tests hash principals and resources.
- Retrieval tests allow eligible caller/resource pairs.
- Retrieval tests deny missing, stale, ambiguous, and mismatched snapshots.
- Evidence pack tests prove raw provider principal IDs are absent.
- Relationship expansion tests re-filter related chunks through provider ACLs.

### Acceptance Gate

- Retrieval cannot return protected provider data unless the caller is eligible in
  a current ACL snapshot.

## Workstream 5: Evidence And Docs

### Problem

Runbooks exist, but there is no dated staging evidence for restore, rollback,
load, or cost drills. Docs also need to track current blocker status as each
workstream lands.

### Implementation Plan

- Add a drill evidence template under `docs/operations/evidence/`.
- Add static tests requiring each evidence record to include date, environment,
  owner, commands or workflow URLs, result, residual risk, and follow-up issue.
- Run restore drill after lifecycle migrations and worker paths are deployed to a
  staging or disposable beta environment.
- Run rollback drill after lifecycle and billing migrations are reversible.
- Run load drill after ACL retrieval and billing meters are wired.
- Run cost drill with fixture Slack, GitHub, Linear, and repo-doc ingestion.
- Update `docs/current-state.md` after each blocker changes state.
- Keep Phase 22 launch checklist in invite-only beta until all blockers have
  passing evidence.

### Primary Files

- `docs/current-state.md`
- `docs/non-ui-enterprise-readiness-autoplan.md`
- `docs/non-ui-enterprise-readiness-test-plan.md`
- `docs/phases/phase-22-enterprise-readiness/`
- `docs/operations/evidence/`
- `tests/deployment/test_enterprise_readiness_docs.py`

### Tests

- Static tests for drill evidence schema.
- Static tests for Phase 22 launch blockers.
- Static tests that docs do not claim broad paid or enterprise self-serve readiness
  until durable lifecycle, billing, ACL, and drill evidence are complete.

### Acceptance Gate

- Every launch claim has a dated evidence record or remains listed as a blocker.

## Sequencing

| Order | Slice | Why first or later |
|---:|---|---|
| 1 | Lifecycle correctness | Fixes P1 compliance defects before adding production entrypoints. |
| 2 | Lifecycle production execution | Builds on the corrected service and executor semantics. |
| 3 | Durable billing and Stripe | Keeps plan enforcement state durable before external provider events arrive. |
| 4 | Provider ACL snapshots | Requires stable connector metadata and retrieval contract changes. |
| 5 | Evidence and docs | Final drill evidence should test the controls that actually ship. |

## Cross-Workstream Test Matrix

| Risk | Required test |
|---|---|
| SQL lifecycle repository returns coroutines through service | Async service/repository contract test. |
| Object-level chunks survive deletion | Mixed object/file chunk deletion regression test. |
| Vector payload remains after tombstone completion | Vector mismatch tombstone failure test. |
| Billing usage disappears on restart | SQL billing persistence integration test. |
| Stripe webhook replay changes state twice | Webhook idempotency test. |
| Provider ACL snapshot is missing or stale | Retrieval fail-closed integration test. |
| Docs overclaim launch readiness | Phase 22 static blocker test. |

## DX Review

Formal `/plan-devex-review` is not installed in this local skill set. Manual DX
requirements:

- Use stable error codes for lifecycle and billing failures.
- Return job IDs and status endpoints for long-running deletion/export work.
- Keep operator docs close to the commands they validate.
- Make failed tombstones repairable by preserving counts and error codes.
- Keep test fixtures deterministic and free of provider secrets.

## Final Approval Gate

Taste decisions surfaced:

- Use one async lifecycle service contract rather than sync wrappers around SQL.
  This is cleaner for the existing async repository style, but it requires updating
  current lifecycle tests.
- Use ACL snapshots rather than live provider checks per retrieval. This is faster
  and auditable, but it requires freshness SLOs and fail-closed stale behavior.

Recommendation: approve as-is and implement Workstream 1 first.

## GSTACK REVIEW REPORT

| Review | Command | Purpose | Runs | Status | Findings |
|---|---|---|---:|---|---|
| CEO Review | `/plan-ceo-review` via `/autoplan` | Scope and sequencing | 1 | issues_open | Fix lifecycle correctness before production wiring; keep UI out of scope. |
| Design Review | `/plan-design-review` | UI/UX | 0 | skipped | No UI scope by user instruction. |
| Eng Review | `/plan-eng-review` via `/autoplan` | Architecture, data flow, tests | 1 | issues_open | Async lifecycle, deletion coverage, durable billing, ACL snapshots, and drill evidence need implementation. |
| DX Review | `/plan-devex-review` | Operator/API experience | 0 | degraded | Skill not installed; manual DX requirements included. |
| Outside Voices | Codex CLI/subagent | Independent challenge | 0 | degraded | Not run in this local follow-up planning pass. |
