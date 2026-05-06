# ADR-003: Hosted-First Data Boundary

## Status

Accepted.

## Decision

Build v1 as hosted-first: Cortex hosts tenant metadata, source-derived content,
indexes, evidence packs, and canonical decisions.

## What It Is

Customers connect Slack, Linear, GitHub, and repo docs to the hosted Cortex
service. Cortex stores encrypted source-derived data and serves agent context
through a local MCP proxy.

## Why Cortex Uses It

- Fastest path to a working product.
- Easier to debug connector, ingestion, index, and retrieval issues.
- Lower deployment friction for early users.
- Still allows a later customer-managed data plane if the market demands it.

## Alternatives Considered

- Hybrid hosted control plane plus customer-managed data plane from day one.
- On-prem/self-hosted first.

## Why Alternatives Lost

- Hybrid-first slows product iteration and requires enterprise deployment
  machinery before the core workflow is proven.
- On-prem-first raises support, upgrade, and observability burden too early.

## Tradeoffs

- Some enterprise buyers may require customer-managed data.
- Hosted data increases security and compliance expectations.
- Token handling, source allowlists, encryption, and audit trails matter early.

## Failure Modes

- Weak tenant isolation could expose customer data.
- Over-broad source ingestion could index sensitive channels/repos.
- Poor deletion/export support could block serious adoption.

## How We Test It

- Tenant isolation tests.
- Source allowlist tests.
- Audit log tests for retrieval and approval records.
- Deletion/export design before broad customer rollout.

## How This Maps From CortexG

`cortexg` explored customer data-plane boundaries in docs, but its runnable demo
was local. Cortex makes hosted-first explicit for v1.

