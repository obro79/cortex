# Phase 8: Real Slack Connector

Phase source of truth: [`../implementation-roadmap.md`](../implementation-roadmap.md#phase-8-real-slack-connector)

Artifacts:

- [`plan.md`](plan.md)
- [`implementation-checklist.md`](implementation-checklist.md)
- [`test-plan.md`](test-plan.md)
- [`autoplan-review.md`](autoplan-review.md)
- [`plan-eng-review.md`](plan-eng-review.md)

Goal: replace fixture Slack ingestion with a production-shaped Slack connector
that uses OAuth, selected-channel backfill, Slack Events API intake, cursor/retry
tracking, and the same raw-event pipeline already proven by fixtures.
