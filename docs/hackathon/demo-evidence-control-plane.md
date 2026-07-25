# Demo Evidence Control Plane

`scripts/demo_evidence_report.py` turns the existing COR-123 fixture rehearsal
into a compact, audience-facing evidence summary. It is deliberately a
fixture-only control plane, not an ingestion connector or an API route.

Run it from the repository root:

```bash
uv run python scripts/demo_evidence_report.py
uv run python scripts/demo_evidence_report.py --format json
```

The report is deterministic and contains only these safe fields:

- provider and media derivative counts;
- completed pipeline stage counts and a simulated `t+N` ingest timeline;
- fixture query, evidence, gate, and handoff statuses;
- an explicit `live_data: false` disclosure.

It never emits source content, URLs, source IDs, event IDs, timestamps, or
credentials. The COR-123 fixture gate blocks, so the report intentionally says
`blocked_pending_human_review` rather than presenting the result as safe to
handoff.

## Future API integration

An API owner can instantiate `DemoEvidenceControlPlane` and return
`(await control_plane.build_report()).as_dict()` from one authenticated,
fixture-only route. That route must preserve the `live_data: false` disclosure
and must not add source-level details to this audience response.
