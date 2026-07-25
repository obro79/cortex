<!-- /autoplan restore point: /Users/owenfisher/.gstack/projects/cortex/main-autoplan-restore-20260513-193310.md -->

# Non-UI Enterprise Readiness Autoplan

Status: reviewed implementation plan
Base branch: `main`
UI scope: no
DX scope: yes, operator/API/docs only
Generated: 2026-05-14

## Goal

Close the remaining non-UI enterprise readiness blockers without expanding into
customer admin UI polish.

## Workstreams

1. Lifecycle execution: implement real deletion and export workers against stored
   raw events, source objects, source files, chunks, embeddings, vector indexes,
   payload storage, and related repository state.
2. Durable billing: replace in-memory billing enforcement with SQL-backed
   customer, subscription, entitlement, usage, and webhook records, then add
   Stripe checkout, portal, and webhook verification/idempotency.
3. Provider ACLs: add provider-native ACL snapshots so retrieval can enforce
   per-user eligibility beyond source allowlists.
4. Production evidence: run and document restore, rollback, load, and cost
   drills.
5. Docs cleanup: update stale Phase 22 launch checklist and known limitations
   now that connector RBAC and plan enforcement are wired.

## Constraints

- Skip UI work.
- Preserve current tenant isolation, RBAC, connector route hardening, and local
  validation behavior.
- Reuse existing repository, service, and test patterns.
- Fail closed for compliance and permissions ambiguity.
- Do not claim enterprise self-serve readiness until evidence exists.

## Autoplan Result

Proceed, but split the work. The right shape is five backend/ops slices, not one
large "enterprise readiness" merge:

1. lifecycle SQL persistence plus real deletion/export executors,
2. durable billing SQL plus Stripe integration,
3. provider ACL snapshots and retrieval enforcement,
4. production drill evidence,
5. stale Phase 22 doc cleanup.

Design review is skipped because this plan has no UI scope. Formal DX review is
degraded because the local `plan-devex-review` skill is not installed; this plan
still includes operator/API/docs DX checks. External Codex CLI voice was not run
because approval policy blocked exporting local repo context to the CLI service.

## Execution Progress

- Slice 1 lifecycle foundations are now partially implemented: SQL lifecycle
  tables, lifecycle repository mappers, repository-backed deletion/export
  executors, payload deletion hooks, vector-point deletion adapter, and focused
  tests are in place.
- Slice 1 still needs production worker/API wiring and staging drill evidence.
- Durable billing/Stripe, provider ACL snapshots, and production drills remain
  open.

## Premise Gate

The user explicitly supplied the five target workstreams in the current request,
so the premise gate is treated as passed for those workstreams only. No hidden UI
or product-surface expansion is included.

| Premise | Verdict | Why |
|---|---|---|
| Lifecycle execution is the largest compliance blocker. | Accepted | `LifecycleService` now has an executor boundary, but lifecycle persistence is in-memory and no concrete executor deletes SQL, payload, or vector state. |
| Billing must move from in-memory to SQL before Stripe is meaningful. | Accepted | `PlanEnforcementService` depends on `InMemoryBillingRepository`; adding Stripe first would create webhook state without durable entitlements. |
| Provider ACLs must replace source allowlist-only retrieval for enterprise claims. | Accepted | Retrieval can use permission scopes and source allowlists, but there is no per-user provider ACL snapshot model. |
| Production evidence requires real drill records. | Accepted with sequencing | Restore, rollback, load, and cost drills are only useful after the data/control planes above have durable targets. |
| Phase 22 docs are stale after connector RBAC/plan hardening. | Accepted | `known-limitations.md` and `launch-checklist.md` still say some route wiring and connector APIs are incomplete. |

## Not In Scope

- Customer admin UI polish, browser onboarding completion, visual design, or
  navigation work.
- SSO, SCIM, enterprise identity provider management, or customer support console
  buildout.
- Provider live API authorization checks on every retrieval request. The selected
  model is snapshot-based ACL enforcement with fail-closed staleness handling.
- Production destructive drills against real customer data. Drill records must
  use staging or disposable beta environments.

## What Already Exists

| Area | Existing leverage |
|---|---|
| Raw events | `src/cortex/ingestion/raw_events.py` has in-memory and SQL repositories, status transitions, idempotency checks, and `DELETED` status. |
| Source objects/files | `src/cortex/normalization/repositories.py` has in-memory and SQL repositories plus `mark_deleted` transitions. |
| Chunks | `src/cortex/chunking/repositories.py` has in-memory and SQL repositories; `SourceChunkStatus.DELETED` exists but no delete transition method. |
| Embeddings | `src/cortex/embeddings/repositories.py` has in-memory and SQL repositories; `EmbeddingJobStatus.STALE` exists but no bulk stale/delete path. |
| Vector index | `src/cortex/interfaces/vector_index.py` exposes `delete(collection, point_id)` and `InMemoryVectorIndex` implements it. |
| Payload storage | `InMemoryPayloadStore` and `FilePayloadStore` can read/write by ref but cannot delete or export. |
| Lifecycle | `LifecycleService.execute_deletion()` creates tombstones and audits executor success/failure, but repository is in-memory only. |
| Billing | `InMemoryBillingRepository` and `PlanEnforcementService` model customers, subscriptions, usage meters, and limits. |
| Permissions | `PermissionScope`, source allowlist filtering, and retrieval fail-closed paths exist, but provider principal ACLs do not. |
| Operations | Backup/restore and production runbooks exist; scripts cover static/local smoke, not recorded staging drills. |

## Dream State Delta

```text
CURRENT
  Invite-only beta backend
  In-memory billing/lifecycle
  Source allowlist permissions
  Runbooks without staging drill evidence

THIS PLAN
  Durable lifecycle and billing records
  Real deletion/export execution
  Provider ACL snapshots in retrieval decisions
  Evidence-backed beta operations gate

12-MONTH IDEAL
  Enterprise self-serve readiness
  Auditable compliance jobs
  Billing and limits reconciled from provider webhooks
  Provider-native ACL parity with freshness SLOs
  Repeatable production drills in CI/release cadence
```

## Implementation Alternatives

| Approach | Effort | Risk | Decision |
|---|---:|---|---|
| One mega enterprise-readiness branch | High | High merge risk, weak review boundaries, hard rollback. | Rejected |
| Five sequential backend slices | Medium | Longer calendar time, but clear validation gates. | Accepted |
| Only patch docs and leave execution stubs | Low | Would preserve known compliance and billing blockers. | Rejected |

## Scope Decisions

| # | Decision | Classification | Principle | Rationale |
|---:|---|---|---|---|
| 1 | Split work into lifecycle, billing, ACL, ops evidence, and docs slices. | Mechanical | Completeness | Each slice has distinct data models, tests, and rollback risk. |
| 2 | Implement lifecycle persistence before deletion/export executors. | Mechanical | Explicit over clever | Executors need durable job and tombstone records before they can be trusted. |
| 3 | Implement SQL billing before Stripe checkout and webhooks. | Mechanical | DRY | Existing enforcement API can be backed by SQL without changing route callers. |
| 4 | Use provider ACL snapshots, not live provider checks on every retrieval. | Taste | Pragmatic | Snapshots are auditable and available during retrieval; live checks add latency and outage coupling. |
| 5 | Sequence production drills after lifecycle, billing, and ACL controls land. | Mechanical | Bias toward action | Drilling before the target controls exist creates evidence for the wrong system. |
| 6 | Update Phase 22 docs twice: now for stale route facts, then after blockers land. | Mechanical | Completeness | The docs should be accurate during the work and become launch evidence later. |

## Decision Audit Trail

| # | Phase | Decision | Classification | Principle | Rationale | Rejected |
|---:|---|---|---|---|---|---|
| 1 | Intake | Treat the five pasted workstreams as the approved premise set. | Mechanical | Bias toward action | The current user request names the scope directly. | Re-opening onboarding/UI scope. |
| 2 | CEO | Keep this as backend/ops work and skip UI. | Mechanical | Explicit over clever | UI work was explicitly excluded and is not needed for these blockers. | Admin UI completion in this plan. |
| 3 | CEO | Split implementation into five slices. | Mechanical | Completeness | Each slice has different persistence, security, and validation needs. | One mega readiness branch. |
| 4 | CEO | Prioritize lifecycle before production evidence. | Mechanical | Completeness | Restore/load evidence is more meaningful after compliance storage paths exist. | Running only current static smokes. |
| 5 | Eng | Add SQL lifecycle repository before real executors. | Mechanical | Explicit over clever | Executors need durable tombstone/export state for retries and audits. | In-memory executor-only implementation. |
| 6 | Eng | Add SQL billing repository before Stripe. | Mechanical | DRY | Current enforcement API can keep its shape while persistence changes below it. | Stripe-only integration on in-memory state. |
| 7 | Eng | Use provider ACL snapshots for retrieval authorization. | Taste | Pragmatic | Snapshots are auditable and avoid live-provider latency/outage coupling. | Live provider checks per retrieval request. |
| 8 | DX | Add explicit drill evidence records. | Mechanical | Completeness | Runbooks without dated evidence do not support launch claims. | Narrative-only operations docs. |

## CEO Review

Mode: selective expansion.

The strategic risk is not that this plan is too large. The risk is claiming
enterprise readiness while the irreversible parts, deletion, billing, and
permissions, are still local or advisory. The plan should bias toward durable
control-plane work and resist adding more customer-facing surface until these
paths are testable.

### Error And Rescue Registry

| Error path | User or operator impact | Rescue behavior |
|---|---|---|
| Deletion executor partially deletes SQL but fails vector cleanup. | Compliance job cannot be trusted. | Mark tombstone failed with per-store counts, keep retryable repair context, do not claim completion. |
| Export worker omits payload/file content referenced by source records. | Customer receives incomplete export. | Manifest must include skipped refs with reason and fail unless omission is explicitly allowed. |
| Stripe webhook repeats or arrives out of order. | Entitlements flap or usage limits misapply. | Store provider event IDs, process idempotently, and prefer latest provider timestamps per subscription. |
| ACL snapshot is stale or missing for a provider resource. | Retrieval could over-share or under-serve. | Fail closed for protected resources and surface permission ambiguity in evidence metadata. |
| Production drill uses local smoke only. | Launch checklist overstates readiness. | Drill records must name environment, commands/workflow URLs, results, and residual risk. |

### Failure Modes Registry

| Failure mode | Severity | Required mitigation |
|---|---|---|
| SQL row status says deleted while payload bytes remain readable. | Critical | Payload store delete/export API plus verification step keyed by stored refs. |
| Vector point remains after embedding row is stale/deleted. | Critical | Delete points by `qdrant_collection` and `qdrant_point_id`; record count mismatch as failure. |
| Source chunk text remains active after source object deletion. | Critical | Bulk chunk status transition or hard delete by workspace/source object/file. |
| Billing usage increments before durable transaction commits. | High | SQL usage writes in the same unit of work as enforcement-sensitive action or a compensating idempotent meter. |
| ACL snapshots store raw provider user IDs. | High | Hash external principal IDs, store provider/resource type, and keep raw IDs out of diagnostics. |
| Docs claim RBAC is incomplete after routes were hardened. | Medium | Update Phase 22 docs now and point to current tests. |

### CEO Dual Voices

External Codex CLI voice: unavailable. The approval policy rejected exporting
local repository plan/context to the CLI service. Claude subagent voice:
unavailable in this runtime. This autoplan therefore runs in single-reviewer
mode and records the degradation.

| Dimension | Primary reviewer | External voice | Consensus |
|---|---|---|---|
| Premises valid? | Yes | N/A | Single-reviewer |
| Right problem to solve? | Yes | N/A | Single-reviewer |
| Scope calibration correct? | Yes, if split into slices | N/A | Single-reviewer |
| Alternatives sufficiently explored? | Yes | N/A | Single-reviewer |
| Competitive/market risks covered? | Partially | N/A | Needs production evidence |
| 6-month trajectory sound? | Yes if ACL and lifecycle are not deferred | N/A | Single-reviewer |

## Design Review

Skipped. No UI scope was detected and the user explicitly asked to skip UI.

## Engineering Review

### Architecture

```text
Public/Admin API
  -> auth/dependencies.py
  -> BillingPlanEnforcementService
        -> SqlAlchemyBillingRepository
        -> StripeBillingGateway

Lifecycle API/worker
  -> LifecycleService
        -> SqlAlchemyLifecycleRepository
        -> SqlAlchemyLifecycleDeletionExecutor
              -> RawEventRepository
              -> SourceObjectRepository
              -> SourceFileRepository
              -> SourceChunkRepository
              -> EmbeddingRecordRepository
              -> Index/vector cleanup
              -> PayloadStore deletion/export
        -> LifecycleExportExecutor
              -> SQL readers
              -> PayloadStore reader
              -> Export manifest writer

RetrievalService
  -> PermissionService
        -> PermissionScopeRepository
        -> ProviderAclSnapshotRepository
        -> principal/resource eligibility check
  -> EvidencePackBuilder
        -> permission exclusions and snapshot hashes
```

The dependency direction should stay one-way: lifecycle and billing services
coordinate repositories, but low-level ingestion, normalization, chunking, and
embedding repositories should not import lifecycle or billing.

### Implementation Plan

#### Slice 1: Lifecycle Persistence And Execution

- Add SQL tables and migration for retention policies, deletion tombstones, and
  export jobs.
- Convert lifecycle repository access behind a protocol with in-memory and
  SQLAlchemy implementations.
- Add deletion methods to raw event, source object, source file, source chunk,
  embedding, index job, and payload/vector surfaces.
- Implement a `SqlAlchemyLifecycleDeletionExecutor` that deletes or tombstones by
  `workspace_id` plus target type.
- Implement export executor that writes a manifest plus JSONL payloads for raw
  events, source objects/files, chunks, embeddings metadata, retrieval/evidence
  metadata, and skipped refs.
- Verify every executor returns per-store counts and fails on count mismatches.

#### Slice 2: Durable Billing And Stripe

- Add billing customer, subscription, usage meter, entitlement, and webhook event
  tables.
- Implement `SqlAlchemyBillingRepository` with the same public methods as
  `InMemoryBillingRepository`.
- Wire app dependencies so public routes use SQL-backed enforcement outside
  tests/dev fixtures.
- Add Stripe gateway abstraction for checkout session, billing portal, webhook
  signature verification, subscription upsert, cancellation, grace, and lock
  states.
- Persist webhook provider event IDs and process idempotently.
- Add reconciliation tests that entitlement decisions follow durable
  subscriptions and usage rows.

#### Slice 3: Provider ACL Snapshots

- Add provider ACL snapshot tables with hashed principal IDs and hashed provider
  resource IDs.
- Add provider-specific snapshot builders for Slack channels/users, GitHub
  repositories/teams/collaborators, Linear teams/projects, and repo-doc roots.
- Extend `PermissionService.check_chunk()` to accept caller principal context and
  require provider ACL eligibility for protected chunks.
- Store ACL snapshot hash on retrieval requests and evidence packs.
- Fail closed when a provider ACL snapshot is missing, stale, or ambiguous.

#### Slice 4: Production Evidence

- Add drill record docs under `docs/runbooks/evidence/` or
  `docs/operations/evidence/`.
- Run staging restore and rollback drills after lifecycle/billing migrations are
  present.
- Run beta load and cost drills after provider ACL and billing meters are wired.
- Record commands, environment, owner, result, residual risk, and follow-up
  issues for each drill.

#### Slice 5: Docs Cleanup

- Update Phase 22 `launch-checklist.md` and `known-limitations.md` immediately to
  reflect connector route RBAC, connector API source selection, and GitHub
  webhook hardening.
- Keep lifecycle execution, durable billing, provider ACL parity, and production
  drills as blockers until the slices above land.
- Link `docs/current-state.md` and this autoplan from the Phase 22 packet.

### Test Diagram

```text
Lifecycle deletion request
  -> SQL tombstone created                         [unit + integration]
  -> raw events marked/deleted by workspace target [integration]
  -> source objects/files/chunks removed/staled    [integration]
  -> embeddings/index jobs staled                  [integration]
  -> vector points deleted                         [unit with fake vector index]
  -> payload refs deleted or skipped with reason   [unit + integration]
  -> tombstone completed with counts               [unit + integration]
  -> partial failure records failed tombstone      [unit]

Lifecycle export request
  -> export job created                            [unit]
  -> manifest contains all stores                  [integration]
  -> payload/file refs exported or skipped         [integration]
  -> hashes/counts match source records            [integration]

Billing enforcement
  -> SQL customer/subscription active              [unit + integration]
  -> usage increment under limit                   [unit + route]
  -> over-limit denied without increment           [unit + route]
  -> Stripe webhook duplicate ignored              [unit]
  -> out-of-order provider event safe              [unit]

Provider ACL retrieval
  -> snapshot builder hashes principals/resources  [unit]
  -> allowed user gets eligible chunks             [integration]
  -> missing/stale ACL fails closed                [integration]
  -> evidence records permission exclusions        [integration]

Operations/docs
  -> drill record schema present                   [unit/static]
  -> Phase 22 docs match current blockers          [unit/static]
```

### Performance Review

- Deletion/export executors need batch queries by `workspace_id`, target type,
  and source connection/source object IDs. Avoid loading full workspaces into
  memory for export.
- ACL checks must not create an N+1 query during retrieval. Load applicable
  snapshot entries in bulk by workspace, provider, resource IDs, and principal
  hash.
- Stripe webhook processing must be idempotent and short-lived; long
  reconciliation should be a follow-up job, not inline webhook work.
- Production load drills must include worker lag, deadletter count, database
  CPU, model calls, storage growth, and retrieval p95.

### Security Review

- Deletion and export APIs must require security/admin role checks and workspace
  context.
- Export manifests must not include provider tokens, session tokens, raw private
  URLs, or unhashed provider principal IDs.
- ACL snapshots must hash external user/group IDs and avoid raw membership dumps
  in logs.
- Stripe webhook verification must reject unsigned payloads and never trust plan
  IDs from client-provided checkout metadata without server-side lookup.

### Worktree Parallelization Strategy

| Lane | Work | Modules touched | Depends on |
|---|---|---|---|
| A | Lifecycle persistence/executors | `lifecycle`, `ingestion`, `normalization`, `chunking`, `embeddings`, `indexing`, `interfaces`, Alembic | Current lifecycle executor seam |
| B | Billing SQL/Stripe | `billing`, `auth/dependencies.py`, API app wiring, Alembic | Existing `PlanEnforcementService` |
| C | Provider ACL snapshots | `permissions`, `retrieval`, connector metadata, Alembic | Current permission scopes |
| D | Ops evidence and docs | `docs/runbooks`, `docs/phases/phase-22-enterprise-readiness` | A/B/C for final evidence, can start static templates now |

Lanes A, B, and C should be separate branches or commits. Lane D can start with
Phase 22 cleanup now and finish drill evidence after A/B/C.

## DX Review

Formal `/plan-devex-review` is unavailable in this local gstack install. Manual
DX checks still apply because the work changes operator docs, webhooks, and API
behavior.

| Dimension | Score | Required improvement |
|---|---:|---|
| Operator setup clarity | 6/10 | Add exact commands/env vars for Stripe webhook verification and drill runs. |
| Error messages | 7/10 | Lifecycle and billing failures should return stable codes, not provider exception text. |
| API consistency | 8/10 | Reuse current FastAPI dependency and error patterns. |
| Docs findability | 6/10 | Link current-state, Phase 22, and drill evidence from one readiness index. |
| Upgrade path | 5/10 | Migrations need rollback notes and beta data backfill guidance. |

## Cross-Phase Themes

- Durability before integrations: lifecycle and billing both need SQL state before
  their external or worker paths are credible.
- Fail closed: deletion, export, webhook verification, and ACL ambiguity all need
  explicit failure states rather than best-effort success.
- Evidence over claims: Phase 22 docs should track only behavior that is wired,
  tested, and drilled.

## Test Plan Artifact

Detailed test plan: `docs/non-ui-enterprise-readiness-test-plan.md`.

## Deferred To Later

- Customer admin UI completion.
- SSO/SCIM enterprise identity.
- Live provider authorization checks per retrieval request.
- Hosted support console.

## Final Approval Gate

Plan summary: implement the remaining non-UI enterprise blockers as separate
backend/ops slices, with lifecycle and billing durability first, ACL snapshots
next, production evidence after the controls exist, and Phase 22 docs kept
accurate throughout.

Decisions made: 8 total. Seven are mechanical. One is a taste decision:
provider ACL snapshots are recommended over live provider checks during every
retrieval request. The snapshot model is lower latency, auditable, and keeps
retrieval available during provider outages, but it needs freshness SLOs and
fail-closed stale-snapshot behavior.

User challenges: none. The plan preserves the user's stated workstreams and UI
exclusion.

Recommended approval: approve as-is and implement Slice 1 first.

## GSTACK REVIEW REPORT

| Review | Command | Purpose | Runs | Status | Findings |
|---|---|---|---:|---|---|
| CEO Review | `/plan-ceo-review` via `/autoplan` | Scope and strategy | 1 | issues_open | Split work into durable backend slices; do not claim enterprise readiness yet. |
| Design Review | `/plan-design-review` | UI/UX | 0 | skipped | No UI scope by user instruction. |
| Eng Review | `/plan-eng-review` via `/autoplan` | Architecture and tests | 1 | issues_open | Lifecycle, billing, ACL, and ops evidence need durable implementations. |
| DX Review | `/plan-devex-review` | Developer/operator experience | 0 | degraded | Skill not installed; manual DX notes included. |
| Outside Voices | Codex CLI/subagent | Independent challenge | 0 | degraded | Codex CLI blocked by privacy approval policy; subagent path unavailable. |
