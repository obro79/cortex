# Phase 1 Engineering Review

## Status

Approved for implementation with dev-only isolation.

Phase 1 should prove the first wow demo path with deterministic fixtures while
staying clearly separate from the production pipeline. It is a harness for
learning, not the durable ingestion architecture.

## Required Guardrails

- `/dev/*` remains disabled unless the explicit workbench flag is enabled.
- Fixture state can be in-memory or local-only; Phase 2 owns durable raw-event
  persistence.
- Use production-shaped contract names and event envelope shapes, but do not
  wire fake paths into production services.
- Deterministic IDs, hashes, timestamps where practical, and stable eval
  outputs are required.
- No real provider tokens, OAuth flows, webhooks, or live source calls.
- Retrieval and gate behavior should be explainable and deterministic, not an
  unreviewable LLM demo.

## Review Findings

1. [P1] Workbench code can accidentally become production code.

   Keep `src/cortex/dev/*` as the boundary. Production route, worker, and
   repository modules should not depend on dev fixture internals.

2. [P1] The demo must prove conflict handling, not just search.

   The COR-123 path should return the stale Redis doc, newer Postgres-session
   evidence, relationship context, and a blocking gate result. If it only shows
   matching snippets, Phase 1 has not proven the product loop.

3. [P2] Determinism needs tests, not convention.

   Tests should assert stable fixture IDs, event IDs or idempotency keys, ranked
   candidates, evidence pack citations, and eval metrics. This prevents the
   workbench from becoming flaky as later phases add contracts.

4. [P2] Dev endpoints need the same content-safety posture as the rest of the
   app.

   Even fixture content should avoid tokens and private raw payloads in event
   envelopes. The workbench can display sample snippets, but pipeline messages
   should stay pointer-oriented.

## Implementation Sequence

1. Add dev fixture repository and deterministic seed/reset.
2. Add pipeline runner with stage timeline records.
3. Add deterministic retrieval and relationship expansion.
4. Add evidence pack builder with stable citations.
5. Add context gate evaluator for allow/warn/block.
6. Add eval runner with fixed expected metrics.
7. Add thin `/dev/*` routes over the service layer.
8. Add server-rendered workbench page.
9. Add endpoint, contract, and determinism tests.

## Review Checklist

- [ ] Dev endpoints unavailable when disabled.
- [ ] Fixture reset and seed are deterministic.
- [ ] Pipeline timeline uses production-shaped event envelopes.
- [ ] COR-123 retrieval returns Slack, Linear, GitHub, docs, and OCR evidence.
- [ ] Evidence citations resolve to fixture source objects/files.
- [ ] Context gate returns the expected blocking conflict.
- [ ] Dev internals are not imported by production services.
