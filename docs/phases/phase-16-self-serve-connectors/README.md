# Phase 16: Self-Serve Connector Setup

Phase 16 turns source setup into customer-admin product flows. A non-developer
workspace admin should be able to connect Slack and GitHub first, then Linear
and repo docs where supported, understand what Cortex will read, and watch data
start flowing.

Phase source of truth: [`../implementation-roadmap.md`](../implementation-roadmap.md#phase-16-self-serve-connector-setup)

## Artifacts

- [Plan](plan.md)
- [Implementation checklist](implementation-checklist.md)
- [Test plan](test-plan.md)
- [Autoplan review](autoplan-review.md)
- [Engineering review](plan-eng-review.md)

## Operating Constraints

- Depends on Phase 15 tenant, auth, membership, and audit boundaries.
- Connector setup actions are workspace-scoped and permission-gated.
- OAuth/install flows must never expose provider tokens or secrets.
- Source selection must clearly explain what Cortex can read.
- Backfills are asynchronous and observable.
