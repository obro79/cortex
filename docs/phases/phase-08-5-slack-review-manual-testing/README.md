# Phase 8.5: Slack Connector Review And Manual Testing

Phase source of truth: [`../implementation-roadmap.md`](../implementation-roadmap.md#phase-85-slack-connector-review-and-manual-testing)

Artifacts:

- [`plan.md`](plan.md)
- [`implementation-checklist.md`](implementation-checklist.md)
- [`test-plan.md`](test-plan.md)
- [`autoplan-review.md`](autoplan-review.md)
- [`plan-eng-review.md`](plan-eng-review.md)
- [`run-logs/2026-05-08-review-report.md`](run-logs/2026-05-08-review-report.md)
- [`run-logs/2026-05-08-data-flow-map.md`](run-logs/2026-05-08-data-flow-map.md)
- [`run-logs/2026-05-08-manual-walkthrough.md`](run-logs/2026-05-08-manual-walkthrough.md)
- [`run-logs/2026-05-08-redaction-and-failure-drills.md`](run-logs/2026-05-08-redaction-and-failure-drills.md)
- [`run-logs/2026-05-08-kafka-slack-e2e-smoke.md`](run-logs/2026-05-08-kafka-slack-e2e-smoke.md)

Goal: stop after Phase 8 and manually prove the Slack connector is safe,
understandable, replayable, and useful before starting Phase 9.

Current decision: `UNBLOCKED_FOR_PHASE_9`. Live-shaped Slack backfill and Event
Subscription payloads now normalize into Slack source objects, chunk into
retrievable Slack evidence, flow through Apache Kafka and durable Postgres state
to deterministic embeddings, and can drive context-gate checks without copying
Slack message text into pipeline event payloads. Gemini remains deferred.
