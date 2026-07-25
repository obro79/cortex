# 05 — Live Slack, Qdrant parity, and provenance-aware retrieval plan

## Outcome and scope

Deliver the one live transition allowed in the final demo: a synthetic Slack
message accepted by the existing signed Slack webhook, canonicalized, indexed,
and exposed as fresh COR-123 evidence. Pair it with a Compose-first/hosted-Qdrant
parity preflight, coverage-aware provenance-preserving rerank, and automated
evidence-contract evaluation. GitHub, Jira, email, Drive/docs, and the agent
checkpoint remain imported snapshots; no other connector becomes live.

The work does not add Slack OAuth, browser ingestion, a general connector UI,
or raw-Qdrant browser access. It reuses the existing Slack OAuth/selection,
signature verifier, backfill, raw event ingress, normalizer, and Qdrant adapter.

## Signed Slack freshness transition

`POST /connectors/slack/events` remains the sole live ingress. It verifies the
Slack timestamp/signature and replay window before decoding/processing the
event, checks the selected synthetic demo channel and workspace installation,
and passes the provider event through the normal `RawEventInput` creation path.
No `live=true` client field exists. Retry headers and Slack event IDs provide
the existing idempotency basis; duplicate signed deliveries cannot create extra
points or graph evidence.

Define a lifecycle-derived freshness state, not a UI assertion:

```text
received (signature verified)
  -> persisted/published
  -> normalized
  -> indexed
  -> graph_eligible_fresh
```

Only `graph_eligible_fresh` lets the COR-123 graph/read-model report the Slack
record as `mode=live, freshness=fresh`. A signature-valid but unfinished event
is `pending`; a retryable/dead-letter event is unavailable and must not appear
as fresh. The ten-second demo target measures signed webhook receipt to
graph-eligible freshness. Trace ID connects webhook, raw event, worker stages,
point ID, evidence pack, and graph projection without exposing Slack payload.

The selected channel must contain synthetic demo messages only. A preflight
asserts channel ID, installation workspace, signature secret availability, and
that the planned text matches the manifest hash after redaction. The operator,
not browser code, posts the synthetic message. If delivery fails, the signed
webhook simulator follows the same route and is recorded `simulated_fallback`;
stage claims and artifacts must visibly say so.

## Local/hosted Qdrant parity

Compose Postgres + Qdrant is mandatory for ordinary development. Preserve one
embedding profile, collection naming rule, point-ID function, payload schema,
vector dimensions/distance, upsert/delete semantics, and retrieval filter
behavior across `QDRANT_URL` targets. Hosted Qdrant is a required final
acceptance target, not a different implementation.

`prepare_cortex_demo preflight --target compose|hosted` performs and reports:

1. database connectivity and migrations; Kafka/worker readiness;
2. Qdrant auth/connectivity, collection/profile/dimension compatibility, and
   expected collection name;
3. Slack configuration, selected channel, signature verifier, and MCP proxy;
4. idempotent corpus seed completion plus expected Postgres/chunk/embedding/
   Qdrant count and point-ID set;
5. a filtered COR-123 query that proves workspace/scope filtering and returns
   the expected snapshot citations;
6. after live delivery, exactly one Slack point, its trace-linked source object,
   fresh graph eligibility, and six-source evidence-contract pass.

The report contains target, timestamps, opaque IDs/counts, profile version,
pass/fail gates, and redacted errors only. It excludes tokens, webhook bodies,
raw Slack content, raw Qdrant payloads, native session material, and private
URLs. Any hosted gate failure exits non-zero and prevents a “hosted verified”
claim. Local Compose remains usable for implementation and recovery.

## Coverage-aware, provenance-preserving rerank

Keep the existing candidate score as the base rank and its individual score
provenance unchanged. Add a deterministic, bounded provider-diversity boost
(not a score rewrite or hard provider quota) for a recognized `COR-123` task.
It selects within the request budget while improving coverage only among
materially relevant candidates. It must never bypass permissions, freshness
filtering, per-source-object limits, or token budget.

Selection rules:

1. deduplicate candidates and compute existing base ranking;
2. identify eligible decisive-provider candidates within a configured relevance
   window of the base rank (priority: live fresh Slack, agent checkpoint,
   GitHub, Jira, email, Drive/docs) and an eligible conflict candidate;
3. select a provider-diverse subset of those candidates only when it does not
   displace a clearly more relevant result; then fill remaining slots by base
   rank, respecting one-source-object cap and the maximum-eight evidence-item
   budget;
4. attach selection provenance without changing existing numeric components:
   `coverage_selected`, `coverage_provider`, `coverage_reason`, and
   `conflict_retained` where applicable;
5. emit `source_coverage`, unavailable/missing provider reasons, and freshness
   state in the evidence pack.

The selector has no right to force an unauthorized, stale-when-fresh-required,
absent, or irrelevant source. Before Slack completes, the answer is explicitly
partial and reports live Slack missing; after it completes, Slack is selected
as fresh evidence when it is relevant. A generic query remains base-ranked
unless its task evidence profile explicitly requests coverage, avoiding hidden
global ranking behavior.

## Tickets

1. **COR-LIVE-501 — Slack state propagation.** Carry verified delivery and
   pipeline-stage status/trace into safe source metadata and graph eligibility;
   ensure duplicates/retries cannot promote freshness incorrectly.
2. **COR-LIVE-502 — Operator live event/preflight.** Add synthetic-channel
   validation, signed simulator recovery, and target-aware `prepare_cortex_demo
   preflight` report/gates.
3. **COR-LIVE-503 — Qdrant parity suite.** Test one shared collection/profile
   contract against Compose and credentialed hosted Qdrant.
4. **COR-LIVE-504 — Coverage selector.** Implement authorized post-rank
   coverage selection and additive provenance/coverage/missing-context output.
5. **COR-LIVE-505 — Golden evidence evaluator.** Automate pre-live partial and
   post-live six-source acceptance, including freshness, conflict, citation,
   and safety-contract checks.

## Validation and acceptance

- Test valid/invalid/expired Slack signatures, selected/unselected channel,
  replay/retry delivery, raw-event idempotency, stage transitions, and no fresh
  graph evidence before indexing.
- Integration-test signed synthetic Slack event through canonical normalization,
  chunking, embedding, Qdrant upsert, scoped retrieval, graph eligibility, and
  trace correlation. Assert p95/observed demo run completes within ten seconds.
- Run parity seed/query/filter/count/point-ID/deletion checks on Compose and
  hosted Qdrant. Hosted credentials are required only for final acceptance;
  missing credentials are a clear blocked gate, never silently skipped.
- Test coverage selection for all six providers, distractor pressure,
  irrelevance protection (no quota-driven displacement), missing Slack, stale
  Drive conflict, per-source caps, token limits, unauthorized and revoked
  sources, and unchanged numeric score provenance.
- Evidence contract passes only when all six citation providers are present,
  Slack is newer/fresh, checkpoint is distinguished as prior agent context,
  Drive is conflicting, the locked middleware/test are cited, and forbidden
  fields are absent from response/report/log capture.

## Safety and truth boundaries

Only a real signed Slack delivery to the configured synthetic channel can be
called `Live`. The webhook simulator is a transparent fallback. Snapshot modes
are immutable and surfaced through retrieval/graph metadata; reranking cannot
upgrade them. Signed acceptance proves event authenticity and origin, not the
truth of message content; evidence retains provenance, timestamp, mode, and
conflict so the agent can state uncertainty. Never expose Slack credentials,
raw Slack/Qdrant payloads, private URLs, transcripts, or native agent handles.
