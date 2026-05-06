# ADR-019: Containerized Services Kubernetes Compatible

## Status

Accepted.

## Decision

Package Cortex services as containers and keep them Kubernetes-compatible, but
do not require Kubernetes for design-partner beta.

## What It Is

Cortex runs as separate containerized services: FastAPI API, connector workers,
normalization workers, chunk/OCR workers, embedding/indexing workers,
retrieval/eval workers, and local MCP proxy. Local development uses Docker
Compose. Beta can use simple hosted container services. Kubernetes is a later
deployment option.

## Why Cortex Uses It

- Containers give consistent runtime packaging.
- Worker types need clear scaling and resource boundaries.
- Kubernetes is useful later for autoscaling and isolation, but early product
  velocity matters more than cluster operations.

## Deployment Path

1. Docker Compose locally.
2. Simple hosted containers for design-partner beta.
3. Kubernetes when queue lag, worker isolation, rolling deploys, or multi-replica
   scaling require it.

## Alternatives Considered

- Kubernetes from day one.
- Single monolith process.
- Serverless functions for all workers.

## Why Alternatives Lost

- Kubernetes day one adds too much operational overhead.
- A monolith blurs API/worker scaling boundaries.
- Serverless functions are awkward for long backfills, Kafka consumers, and
  stateful worker leases.

## Tradeoffs

- Simple hosted containers may have weaker autoscaling than Kubernetes.
- Some deployment decisions are deferred.
- Container boundaries still require good configuration and health checks.

## Failure Modes

- Beta hosting cannot scale long-running backfills.
- Worker resource contention if too many worker types share one container.
- Moving to Kubernetes later exposes missing readiness/liveness metrics.

## How We Test It

- Docker Compose smoke starts API and workers locally.
- Each container exposes health/readiness endpoints or worker heartbeats.
- Worker containers can run independently by role.
- Deployment docs name which services can scale horizontally.

## How This Maps From CortexG

`cortexg` had local/demo data-plane bootstrap ideas. Cortex keeps the
service-separated data-plane shape but avoids requiring Kubernetes before the
workload justifies it.

