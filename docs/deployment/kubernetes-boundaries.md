# Kubernetes-Compatible Boundaries

Phase 12 does not ship Kubernetes manifests. It keeps service boundaries
compatible with a future Kubernetes deployment.

## Probe Mapping

Future probe mapping:

- `api` liveness: `GET /health/live`.
- `api` readiness: `GET /health/ready`.
- `worker-pipeline` liveness: process is running.
- `worker-pipeline` readiness: worker heartbeat status is `ready` or
  `starting`, dependency checks pass, and Kafka group membership is healthy.
- `migrate`: one-shot job running `alembic upgrade head`.

Readiness should report clear sanitized failure reasons. It must not include
provider tokens, database passwords, raw source content, private URLs, embeddings,
vectors, or hidden source names.

## Config And Secrets

Future Kubernetes config mapping:

- non-secret settings map to ConfigMaps or environment variables,
- provider tokens and infrastructure credentials map to Secrets or external
  secret injection,
- image labels carry version and revision,
- runtime role is selected by command/args rather than image mutation.

Secrets must stay runtime-only. Images and manifests must not embed OAuth tokens,
webhook secrets, private keys, raw payloads, payload-store files, or local `.env`
files.

## Stateless Services

Horizontally scalable workloads:

- `api`: stateless FastAPI deployment behind ingress.
- `worker-pipeline`: deployment scaled by Kafka consumer group.
- future connector, normalization, chunking, embedding, indexing, relationship,
  retrieval/eval, and ops/repair workers: independent deployments by role.

Workers must remain idempotent around durable records and Kafka event replay.

## Stateful Dependencies

Stateful dependencies remain outside Cortex stateless deployments:

- Postgres,
- Kafka,
- object storage,
- Qdrant,
- optional Redis if a future code path requires ephemeral cache or locks.

Use managed services where possible for beta. Do not run stateful dependencies as
part of the Cortex app deployment unless the host explicitly owns that
operational burden.

## Coordination

Cortex should not add a custom singleton leader. Use:

- Kafka consumer groups for worker distribution,
- Postgres row-level leases or idempotency records where needed,
- explicit migration jobs,
- worker heartbeats for operational visibility.

## Intentionally Not Phase 12

Phase 12 does not include:

- Kubernetes Deployment, Service, Ingress, Job, or Secret manifests,
- HorizontalPodAutoscaler definitions,
- production backup/restore automation,
- custom leader-election controllers,
- public admin UI.
