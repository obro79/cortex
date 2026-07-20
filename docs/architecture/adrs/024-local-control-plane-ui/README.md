# ADR-024: Local, Linear-Inspired Cortex Control Plane

## Status

Accepted — 2026-07-19.

## Context

Cortex's differentiated product interface is MCP: it provides cited company context to an existing agent. A browser UI is still valuable for connecting sources, inspecting ingestion/index health, verifying evidence, and configuring MCP. The current Next scaffold is user-owned, static, and collides with a legacy FastAPI `/ui/*` operations surface.

## Decision

Build a **local-only Next.js control plane** for the hackathon. Design it with Linear-inspired interaction principles—dense but calm workspace navigation, keyboard-friendly command/search flows, list/detail inspection, and concise status language—without copying Linear branding or turning Cortex into a competing chat product.

Next owns `/ui/...`; its same-origin local BFF owns `/api/cortex/...`; FastAPI owns JSON endpoints (`/dev`, `/demo`, `/health`, then `/api/v1`). The legacy FastAPI HTML `/ui/*` is frozen and must not be proxied into the product; move or retire it before a single-host deployment. The BFF is the only browser-to-backend boundary.

## First-release workflow

```text
Context request -> cited evidence -> fixture-pipeline proof -> MCP setup
        -> stale or failed evidence -> health -> retry/backfill
```

The first pages are Context, Evidence, Pipeline Run, Health, and MCP Setup. Sources, connectors, evidence history, and traces appear only behind durable capability gates. The UI can copy a bounded context/evidence handoff into an existing agent but does not own a general conversation history.

## Guardrails

- Local session/workspace identity is resolved server-side; route/body workspace values are not authorization.
- The browser never accesses Qdrant, Kafka, object storage, or Postgres directly.
- Every data view represents loading, empty, no-result, partial, stale, denied, and error states honestly.
- Static fixture claims stay visibly labeled until wired to live APIs.
- Evidence never exposes provider tokens, raw payloads, Qdrant payloads, or protected-content leakage.
- Preserve the dirty frontend scaffold: checkpoint/branch it before implementation and do not overwrite it from the clean backend branch.

## Alternatives considered

1. Keep/extend the FastAPI HTML `/ui` surface.
2. Build a hosted, multi-user UI now.
3. Build a local Next control plane.
4. Build a general Cortex chat application.

The legacy UI is an internal admin surface with mismatched auth and presentation. Hosted UI introduces deployment/auth scope before the retrieval proof is stable. A chat product repeats the agent interface rather than reducing setup friction. The local control plane best supports the hackathon proof and the eventual MCP-first product.

## Consequences

- Typed browser API/session/evidence/source/job contracts are a prerequisite to treating the UI as live.
- Polling is sufficient initially; SSE is deferred until the durable readiness projection exists.
- Frontend lint, typecheck, build, and deterministic end-to-end tests become part of the definition of done.
- Hosted auth/SSO, team administration, billing, and deployment remain deliberately deferred.

The detailed route, fixture-demo, API, accessibility, and delivery plan is in
[the ADR-024 implementation plan](implementation-plan.md).
