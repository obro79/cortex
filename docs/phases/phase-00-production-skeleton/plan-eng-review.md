# Phase 0 Engineering Review

## Status

Approved for implementation with skeleton-only guardrails.

Phase 0 should create a production-shaped repo, not a half-built product. The
engineering bar is stable boundaries: contracts, app shell, worker shell,
configuration, migrations, tests, observability hooks, and local infrastructure.

## Required Guardrails

- Keep product behavior out of Phase 0 unless it is needed to prove the shell.
- Contract models should be broad enough for later phases but not pretend to
  enforce workflow semantics that do not exist yet.
- Dev-only routes must be disabled by default.
- Local defaults should not require Redis, Temporal, Kubernetes, or live
  provider credentials.
- Event envelopes must reject content-bearing payload fields that could leak raw
  text, embeddings, OAuth tokens, or secrets.
- Docker Compose should support local development, not become the production
  deployment contract.

## Review Findings

1. [P1] The skeleton can overreach into domain implementation.

   Phase 0 names many future contracts. Keep them as typed stubs, interfaces,
   and smoke-tested wiring. Do not add real ingestion, retrieval, permission, or
   connector logic before the fixture and pipeline phases own that behavior.

2. [P1] Content-safety checks belong in the event envelope from day one.

   The event envelope is a cross-service primitive. Tests should reject known
   forbidden payload keys so future worker code cannot accidentally move raw
   content, vectors, or tokens through lightweight pipeline messages.

3. [P2] Configuration defaults need production-safe posture.

   Flags for dev workbench, deterministic providers, and optional platform
   components should default off or safe. The app should fail clearly when a
   required dependency is missing and should not silently switch to unsafe local
   behavior in production.

4. [P2] Migration shell should avoid premature full schema commitment.

   Alembic and SQLAlchemy setup are required, but full domain tables should wait
   until the phases that own those data contracts. Add only what is needed for
   smoke tests and future migration hygiene.

## Implementation Sequence

1. Add project metadata, package layout, lint, typecheck, and test commands.
2. Add FastAPI app factory, health route, and dev-route guard.
3. Add settings/config model with safe defaults.
4. Add Pydantic contracts and event envelope validation.
5. Add SQLAlchemy/Alembic shell.
6. Add local interface boundaries for storage, events, workers, cache,
   scheduler, rate limits, and vector index.
7. Add CLI, MCP, and worker entrypoint smoke paths.
8. Add Docker Compose for local dependencies.
9. Add focused tests and docs.

## Review Checklist

- [ ] Dev routes disabled by default.
- [ ] Event envelope rejects raw content, embeddings, tokens, and secrets.
- [ ] CLI, MCP, API, and worker smoke tests pass.
- [ ] Config defaults are safe for production.
- [ ] Optional infrastructure is actually optional in tests.
- [ ] No real connector/retrieval/gate behavior lands in Phase 0.
