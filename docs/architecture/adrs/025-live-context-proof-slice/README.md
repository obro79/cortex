# ADR-025: Live Context Proof Before Source Breadth or UI Polish

## Status

Proposed — 2026-07-20.

## Context

Cortex is meant to be an MCP-first company-context layer. The product needs
one trustworthy proof that a selected real source becomes authorized, cited
context for an existing agent. The repository already contains the ingredients,
but their durable composition is incomplete: scope persistence is absent,
index/query embedding configuration can diverge, and the local MCP process is
not yet an authenticated API proxy.

Adding Drive, Jira, Atlassian, media extraction, or a broader dashboard before
closing these gaps would increase surface area without proving the central
claim.

## Decision

Prioritize a **Live Context Proof** vertical slice:

```text
selected Slack channel
  -> canonical SQL/Kafka pipeline
  -> hosted Qdrant derived index
  -> authorized task-context API
  -> local MCP proxy and local evidence/control-plane view
  -> redacted run ledger
```

Slack is mandatory because it has the most mature selected-source/OAuth/backfill
path and the user already has a workspace. One selected GitHub repository is a
second milestone only after the Slack path is verified. Drive/Jira may appear
as explicitly labelled imported snapshots, not live integrations.

The slice uses one shared `EmbeddingIndexProfile` for document and query
embeddings and one settings-derived Qdrant collection. It adds persisted
permission scopes and retains fail-closed authorization behavior. A local MCP
proxy forwards `get_task_context` to the API; it never receives workspace
authority from tool input and never accesses native agent sessions.

The output includes a redacted `DemoRunReport` to prove ingestion/index/query
counts and a source mode (`live`, `imported_snapshot`, or `fixture`) to make
demo claims auditable.

The first credential-free implementation is an immutable SQL projection of a
validated, redacted report. It is intentionally not a reconstruction from
mutable workspace-wide state: an exact automatic report requires a later
run-membership ledger propagated through every pipeline and query stage.

## Alternatives considered

1. Build all requested connectors first.
2. Polish/rewrite the dashboard before runtime proof.
3. Continue using the fixture packet as the primary demo.
4. Build the Live Context Proof first.

Connector breadth lacks the shared verified path that every connector needs.
Dashboard polish cannot repair an unavailable durable query. The fixture packet
is useful and should remain a labelled recovery path, but it does not prove
live company context. The vertical proof is the smallest credible basis for
the MCP product story.

## Consequences

- Hosted Qdrant credentials and the approved Slack source are needed only for
  the operator acceptance run, never for unit tests or browser code.
- The first recording can demonstrate Slack plus any clearly-labelled snapshot
  sources; it must not overclaim live multi-provider sync.
- GitHub persistence and cross-source linking are next only after a green Slack
  proof.
- UI scope remains Context, Evidence, and Health. General chat, hosted admin,
  and full connector UX stay deferred.
- Every recorded count, screenshot, slide, and video claim must be reproducible
  from a saved redacted run report.

## Acceptance

The decision is complete when the Slack-to-MCP path, failure/security matrix,
and report/UI proof gates in the [Live Context Proof Slice specification](../../../specs/2026-07-20-live-context-proof-slice.md)
are green.
