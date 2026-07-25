# Current State

Last updated: 2026-05-15

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
- GitHub webhooks now reject selected-repository source mismatches, and Slack
  webhooks ignore provider team IDs that do not map to an active installation.
- Slack source selection validates that the OAuth installation belongs to the
  requested workspace before billing plan quota is consumed.
- The app factory registers in-memory billing for local/test mode and SQL-backed
  billing repositories plus async plan enforcement for SQL mode.
- SQL mode now wires public tenant resolution to the SQL tenant repository
  instead of falling back to the in-memory tenant repository.
- Stripe checkout/portal session creation is behind an injectable gateway, and
  verified Stripe webhooks are recorded idempotently before synchronizing local
  billing state.
- Customer-facing checkout, portal, and Stripe webhook API routes are present
  and permissioned for billing admins where applicable.
- Lifecycle deletion now has repository-backed executor foundations: deletion
  creates a hashed tombstone, deletes or tombstones repository data, removes
  payload/vector refs where wired, completes or fails the tombstone, and records
  an audit trail.
- Lifecycle deletion/export has API request/status/lease/execute/retry routes,
  an SQL lifecycle worker role, and Qdrant vector deletion support.
- Lifecycle persistence tables now exist for retention policies, deletion
  tombstones, and export jobs.
- Provider-native ACL snapshots can now be attached to permission checks so
  protected connector chunks fail closed on missing, stale, or non-matching ACLs.
- Provider ACL ingestion collectors can pull Slack channel members, GitHub
  repository collaborators, and Linear team members, then persist hashed
  snapshot entries and authenticated user-to-provider-principal mappings.
- Provider ACL freshness reporting can flag stale and missing snapshots without
  logging raw provider IDs.
- A SQL-only `provider-acl` worker role can run scheduled, singleton provider
  ACL refreshes from config-driven targets while keeping tokens in runtime env.
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
- Production Stripe credentials and live checkout/portal/webhook smoke tests
  remain launch-gated.

### Lifecycle and Compliance

- Retention policy models, sweep planning, export job models, deletion job
  models, SQL lifecycle persistence tables, tombstones, and audit events exist.
- Repository-backed deletion/export executor foundations cover raw events,
  source objects, source files, source chunks, embeddings, index jobs, vector
  points, and payload refs for local repository-backed flows.
- SQL-compatible lifecycle service and executor boundaries are async-safe, and
  deletion tombstones fail closed on cleanup mismatches.
- Staging deletion/export drill evidence is still required before
  deletion/export can be claimed complete.

### Provider ACLs

- Provider ACL snapshot primitives exist for Slack, GitHub, and Linear resource
  references.
- Retrieval permission filtering can require caller provider principals and deny
  protected chunks when snapshots are missing, stale, or non-matching.
- Snapshot ingestion from provider APIs, hashed principal mapping persistence,
  freshness reporting, and a scheduled worker entrypoint are implemented.
  Staging deployment of the schedule and freshness drills are still required.

### Operations

- Docker Compose configuration, deployment docs, hosted container boundaries,
  Kubernetes boundary docs, and runbooks are present.
- Local validation currently covers tests, linting, formatting, typing, Docker
  Compose config, lifecycle/provider ACL worker profiles, migration SQL,
  backend ops smoke checks, and diff whitespace checks.
- Staging restore, rollback, load, and cost drills still need real recorded
  evidence before broad launch.
- Local evidence templates and a hardening evidence log now live under
  `docs/operations/evidence/`.
- A no-secret backend/ops launch gate exists at
  `scripts/backend_ops_launch_gate.py` for local preflight evidence.

## Still Not Done

- End-to-end onboarding/browser flows, invite acceptance, terms gates, logout,
  account deletion, and full CSRF browser coverage.
- Production Stripe activation and live checkout/portal/webhook smoke evidence.
- Staged lifecycle deletion/export drill evidence.
- Deployed provider-native ACL ingestion schedule and freshness drill evidence.
- Full customer admin UI and browser coverage.
- Hosted support console and production drill evidence.
- Dev routes remain public when explicitly feature-enabled and must stay off
  outside local/test deployments.

## Latest Validation

The latest local validation after the production activation hardening work
passed:

- `uv run pytest`: 432 passed
- `uv run ruff check .`: passed
- `uv run ruff format --check .`: passed
- `uv run mypy src`: passed
- `docker compose config`: passed
- `docker compose --profile lifecycle config`: passed
- `docker compose --profile provider-acl config`: passed
- `git diff --check`: passed
- `uv run alembic heads`: passed with one head,
  `0016_provider_principal_mappings`
- `uv run alembic upgrade head --sql`: passed
- `uv run alembic downgrade 0016_provider_principal_mappings:0013_lifecycle_persistence --sql`:
  passed
- `uv run python scripts/backend_ops_launch_gate.py --evidence docs/operations/evidence/2026-05-15-backend-ops-launch-gate-local-evidence.md`:
  passed and recorded no-secret local evidence
- `uv run python scripts/stripe_activation_smoke.py --static --fake-gateway`:
  passed as part of the backend ops launch gate

Deep review follow-up plan:

- `docs/non-ui-enterprise-readiness-followup-autoplan.md`

Recent follow-up blockers closed locally:

- SQL lifecycle service access has async API and worker wiring.
- Source deletion has regression coverage for mixed object-level and file-backed
  chunks.
- Lifecycle tombstones fail closed for vector and payload cleanup mismatches.

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
