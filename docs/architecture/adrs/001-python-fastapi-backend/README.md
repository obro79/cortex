# ADR-001: Python FastAPI Backend

## Status

Accepted.

## Decision

Build the new Cortex backend in Python with FastAPI, Pydantic v2, SQLAlchemy,
Alembic, and async worker processes.

## What It Is

FastAPI provides the hosted HTTP API, OAuth callback routes, health checks, and
admin/debug endpoints. Pydantic models define shared request, event, and storage
contracts. SQLAlchemy/Alembic manage Postgres persistence and migrations.

## Why Cortex Uses It

- Python is the requested backend language.
- FastAPI is a strong fit for typed APIs, async I/O, OAuth callbacks, and
  service-oriented backend work.
- Pydantic makes provider-neutral contracts explicit.
- Python has mature clients for Kafka, Postgres, Qdrant, OCR, embeddings, and
  AI model providers.

## Alternatives Considered

- Next.js/TypeScript core from `cortexg`.
- Django.
- Worker-first minimal Python without a real API framework.

## Why Alternatives Lost

- Next.js/TypeScript is useful as a prototype reference, but the new backend
  should be Python-native.
- Django has useful admin scaffolding, but it is heavier and less natural for
  event-worker architecture.
- A worker-only backend would leave OAuth, health, MCP proxy auth, and admin
  surfaces too custom.

## Tradeoffs

- FastAPI is less batteries-included than Django.
- We need to define our own admin and operational UI later.
- Async correctness becomes important across Kafka consumers and provider APIs.

## Failure Modes

- Blocking I/O inside async routes/workers can reduce throughput.
- Pydantic contracts can drift from database schemas without tests.
- Too much logic in API handlers can blur service boundaries.

## How We Test It

- Contract tests for Pydantic schemas.
- API smoke tests for health, OAuth callback shape, and MCP proxy auth.
- Worker tests that import the same contracts used by API routes.

## How This Maps From CortexG

Keep the `cortexg` concepts: source connections, raw events, source objects,
chunks, embeddings, evidence packs, and MCP tools. Rebuild them in Python.

