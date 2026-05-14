# Current State

Last updated: 2026-05-14

## Status

Cortex is currently an invite-only beta backend with production-shaped ingestion,
retrieval, tenant isolation, billing-enforcement, lifecycle, and operations
foundations. It is not ready for unattended enterprise self-serve rollout or a
broad paid launch.

UI polish and customer admin screen completion are intentionally out of scope for
this snapshot.

## Recently Landed Non-UI Hardening

- Public connector API routes for Slack, GitHub, Linear, and repo-docs now
  require public tenant context, workspace matching, RBAC permission checks, and
  plan enforcement for setup, source-selection, and backfill actions.
- GitHub webhooks fail closed when no webhook secret is configured, and invalid
  signatures return `401 Unauthorized`.
- Slack source selection validates that the OAuth installation belongs to the
  requested workspace before billing plan quota is consumed.
- The app factory registers in-memory billing for local/test mode and SQL-backed
  billing repositories plus async plan enforcement for SQL mode.
- Stripe checkout/portal session creation is behind an injectable gateway, and
  verified Stripe webhooks are recorded idempotently before synchronizing local
  billing state.
- Lifecycle deletion now has repository-backed executor foundations: deletion
  creates a hashed tombstone, deletes or tombstones repository data, removes
  payload/vector refs where wired, completes or fails the tombstone, and records
  an audit trail.
- Lifecycle persistence tables now exist for retention policies, deletion
  tombstones, and export jobs.
- Provider-native ACL snapshots can now be attached to permission checks so
  protected connector chunks fail closed on missing, stale, or non-matching ACLs.
- Tests cover connector tenant/RBAC/plan enforcement and the lifecycle deletion
  executor path.

## Implemented Foundations

### Tenant, Auth, and RBAC

- Tenant domain models, in-memory repositories, migrations, and public tenant
  context dependencies exist.
- Public routes reject internal actor headers and require tenant/workspace
  context before customer-scoped connector actions.
- Owner, admin, member, security, billing, and viewer roles are modeled through
  a permission matrix and enforced on the hardened connector API routes.

### Connectors

- Slack OAuth callback, event ingestion, source selection, source backfill, and
  source listing APIs are implemented with tenant and billing checks.
- GitHub setup, webhook, source listing/selection, and backfill APIs are
  implemented with tenant, RBAC, billing, and signature checks.
- Linear and repo-docs setup/source APIs are implemented with tenant, RBAC, and
  billing checks.
- Provider health, redaction, setup metadata, and shared connector service
  contracts exist.

### Billing and Plan Enforcement

- In-memory org-scoped customers, subscriptions, entitlements, and usage meters
  are implemented for local/test enforcement.
- SQL-backed billing customers, subscriptions, usage meters, usage events, and
  Stripe webhook event records now have models, migrations, and repository
  wiring.
- Public API enforcement is wired for connector source limits and backfill
  actions.
- Stripe webhook signature verification, duplicate-event handling, checkout
  session creation, and billing portal session creation are implemented behind
  testable provider boundaries.
- Production Stripe credentials, live checkout/portal smoke tests, and customer
  plan-management routes remain launch-gated.

### Lifecycle and Compliance

- Retention policy models, sweep planning, export job models, deletion job
  models, SQL lifecycle persistence tables, tombstones, and audit events exist.
- Repository-backed deletion/export executor foundations cover raw events,
  source objects, source files, source chunks, embeddings, index jobs, vector
  points, and payload refs for local repository-backed flows.
- SQL-compatible lifecycle service and executor boundaries are async-safe, and
  deletion tombstones fail closed on cleanup mismatches.
- Production lifecycle API/worker queueing and staging drill evidence are still
  required before deletion/export can be claimed complete.

### Provider ACLs

- Provider ACL snapshot primitives exist for Slack, GitHub, and Linear resource
  references.
- Retrieval permission filtering can require caller provider principals and deny
  protected chunks when snapshots are missing, stale, or non-matching.
- Durable snapshot ingestion from provider APIs and staging freshness drills are
  still required.

### Operations

- Docker Compose configuration, deployment docs, hosted container boundaries,
  Kubernetes boundary docs, and runbooks are present.
- Local validation currently covers tests, linting, formatting, typing, Docker
  Compose config, and diff whitespace checks.
- Staging restore, rollback, load, and cost drills still need real recorded
  evidence before broad launch.
- Local evidence templates and a hardening evidence log now live under
  `docs/operations/evidence/`.

## Still Not Done

- End-to-end onboarding/browser flows, invite acceptance, terms gates, logout,
  account deletion, and full CSRF browser coverage.
- Production Stripe activation, customer plan-management routes, and live
  checkout/portal/webhook smoke evidence.
- Production lifecycle worker queueing and staged deletion/export drill evidence.
- Provider-native ACL snapshot ingestion from real provider APIs and freshness
  drill evidence.
- Full customer admin UI and browser coverage.
- Hosted support console and production drill evidence.
- SQL-backed tenant service wiring beyond current migrations and local/in-memory
  implementations.

## Latest Validation

The latest local validation after the non-UI hardening work passed:

- `uv run pytest`: 396 passed
- `uv run ruff check .`: passed
- `uv run ruff format --check .`: passed
- `uv run mypy src`: passed
- `docker compose config`: passed
- `git diff --check`: passed
- `uv run alembic heads`: passed with one head,
  `0015_provider_acl_snapshots`
- `uv run alembic upgrade head --sql`: passed
- `uv run alembic downgrade 0015_provider_acl_snapshots:0013_lifecycle_persistence --sql`:
  passed

Deep review follow-up plan:

- `docs/non-ui-enterprise-readiness-followup-autoplan.md`

Deep review blockers:

- SQL lifecycle service access currently needs async wiring before production use.
- Source deletion needs regression coverage for mixed object-level and file-backed
  chunks.
- Lifecycle tombstones need fail-closed behavior for vector and payload cleanup
  mismatches.

## Beta Positioning

Safe to claim:

- Invite-only beta backend.
- Guided setup for Slack, GitHub, Linear, and repo-docs ingestion.
- Workspace-scoped retrieval and evidence paths.
- Operator-assisted support with redacted diagnostics.

Do not claim yet:

- Unattended self-serve enterprise readiness.
- Broad paid launch readiness.
- Provider-native ACL parity.
- Complete deletion/export execution.
- Polished customer admin UI.
