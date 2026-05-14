# Non-UI Enterprise Readiness Test Plan

Generated from `docs/non-ui-enterprise-readiness-autoplan.md`.

## Lifecycle Execution

- Unit-test lifecycle SQL repository create/update paths for retention policies,
  deletion tombstones, and export jobs.
- Integration-test deletion for each persisted store:
  - raw events,
  - source objects,
  - source files,
  - source chunks,
  - embedding records,
  - index jobs,
  - vector points,
  - payload refs.
- Verify deletion returns per-store counts and fails the tombstone when any store
  reports a mismatch or raises.
- Verify raw event, source object, source file, and source chunk retrieval paths
  no longer return deleted data.
- Verify vector delete is called with the stored collection and point IDs.
- Verify export manifests include counts, hashes, skipped refs, and destination
  refs without provider tokens or private URLs.

## Durable Billing

- Unit-test SQL-backed customer, subscription, entitlement, and usage repository
  methods against the in-memory contract.
- Route-test source selection and backfill enforcement using SQL billing state.
- Unit-test Stripe webhook signature rejection for missing/invalid signatures.
- Unit-test duplicate webhook provider events are ignored idempotently.
- Unit-test out-of-order subscription events do not downgrade newer state.
- Integration-test checkout and portal session creation with a fake Stripe
  gateway.

## Provider ACL Snapshots

- Unit-test provider ACL snapshot builders hash external principal and resource
  IDs.
- Unit-test Slack, GitHub, Linear, and repo-doc chunk metadata maps to ACL
  resources.
- Integration-test retrieval allows chunks when caller principal is eligible in
  the active snapshot.
- Integration-test retrieval fails closed for missing, stale, or ambiguous ACL
  snapshots.
- Verify evidence packs record permission exclusion counts and snapshot hashes
  without raw provider identities.

## Production Evidence

- Static-test every drill evidence record has date, environment, owner, commands
  or workflow URLs, result, residual risk, and follow-up issues.
- Run restore drill against staging/disposable data after lifecycle migrations.
- Run rollback drill after billing/lifecycle migrations.
- Run load drill after ACL retrieval and billing meters are wired.
- Run cost drill with fixture Slack, GitHub, Linear, and repo-docs data.

## Docs Cleanup

- Static-test Phase 22 known limitations do not claim RBAC route wiring is
  incomplete where current connector routes enforce it.
- Static-test Phase 22 launch checklist still lists durable lifecycle execution,
  durable billing/Stripe, provider ACL parity, and production drills as blockers.
- Link `docs/current-state.md` and
  `docs/non-ui-enterprise-readiness-autoplan.md` from the Phase 22 packet.
