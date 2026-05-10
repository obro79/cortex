# Phase 13: Layer-Later Platform Components

Phase 13 adds only the platform layers that protect real beta usage or make
operations materially easier. Redis/cache, ingress, rate limits, scheduler
leases, backup/restore drills, feature flags, and support tools must stay small,
testable, and aligned with the v1 authority model.

Phase source of truth: [`../implementation-roadmap.md`](../implementation-roadmap.md#phase-13-layer-later-platform-components)

## Artifacts

- [Plan](plan.md)
- [Implementation checklist](implementation-checklist.md)
- [Test plan](test-plan.md)
- [Autoplan review](autoplan-review.md)
- [Engineering review](plan-eng-review.md)

## Operating Constraints

- Postgres remains the transactional source of truth.
- Kafka remains the durable event backbone.
- Object storage remains the durable home for large payloads and source files.
- Qdrant/OpenSearch remain rebuildable derived indexes.
- Redis, if enabled, is ephemeral cache or coordination state only.
- v1 does not add custom distributed storage or a custom single-leader control
  plane.
