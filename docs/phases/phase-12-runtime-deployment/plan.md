# Phase 12 Plan: Runtime Deployment

## Goal

Package Cortex so it can run reliably outside a developer shell:

```txt
container images
  -> Docker Compose local stack
  -> API + independent worker roles
  -> Postgres + Apache Kafka + Qdrant + object storage
  -> health/readiness/worker heartbeats
  -> simple hosted-container config
  -> Kubernetes-compatible boundaries
```

Phase 12 is not a Kubernetes phase. It creates production-shaped runtime
packaging for design-partner beta while keeping local development reproducible.

## Inputs

- [`../implementation-roadmap.md`](../implementation-roadmap.md#phase-12-runtime-deployment)
- [`../../architecture/handbook.md`](../../architecture/handbook.md#runtime-and-deployment-strategy)
- [`../../architecture/review.md`](../../architecture/review.md#deployment-architecture)
- [`../../architecture/adrs/019-containerized-services-kubernetes-compatible/README.md`](../../architecture/adrs/019-containerized-services-kubernetes-compatible/README.md)
- [`../../architecture/adrs/022-apache-kafka-runtime/README.md`](../../architecture/adrs/022-apache-kafka-runtime/README.md)
- [`../phase-11-observability-operations/plan.md`](../phase-11-observability-operations/plan.md)

## Existing Foundation

Earlier phases provide:

- FastAPI API entrypoint,
- worker entrypoints and roles,
- Postgres/Alembic migrations,
- Apache Kafka runtime decision,
- Qdrant adapter,
- object-storage interface,
- health/readiness and observability expectations,
- admin authorization/audit expectations,
- replay/repair and worker heartbeat concepts.

Phase 12 should package these pieces without changing their architecture.

## Non-Goals

- No required Kubernetes manifests for beta.
- No custom distributed storage or custom leader election.
- No production-grade autoscaling system.
- No full backup/restore implementation; Phase 13 deepens backup/restore
  runbooks.
- No public admin UI.
- No new source connectors or retrieval features.
- No self-hosted observability stack.

## Runtime Services

Current containerized service boundaries:

- `api`: FastAPI API, OAuth callbacks, MCP/API endpoints, health/readiness.
- `worker-pipeline`: current durable Kafka pipeline worker using
  `cortex-worker --role pipeline`.
- `worker-noop`: smoke/test role using `cortex-worker --role noop`.
- `migrate`: one-shot migration command/service that runs Alembic before API or
  workers are promoted to ready.
- `mcp-proxy`: local process or optional container; not required inside hosted
  backend deployment.

Future Kubernetes-compatible role boundaries to document, but not require until
the worker CLI exposes concrete roles:

- connector/ingestion workers,
- normalization workers,
- chunk/OCR workers,
- embedding/indexing workers,
- relationship workers,
- retrieval/eval workers,
- ops/repair workers.

Supporting services for local Compose:

- Postgres,
- Apache Kafka in KRaft mode using `apache/kafka:4.2.0`,
- Qdrant,
- MinIO object storage compatible with the storage interface,
- optional Redis only if already needed for ephemeral cache/locks.

## Container Images

Build images for:

- API,
- worker image with role selected by env/command,
- optional local MCP proxy image if useful.

Image requirements:

- non-root runtime user where practical,
- deterministic dependency install from the project lockfile or another pinned
  dependency source,
- small enough for beta iteration,
- healthcheck command for API image,
- worker command supports `--role`,
- no secrets baked into images,
- `.dockerignore` or equivalent build-context guardrails prevent local env
  files, run logs, payload stores, caches, and secrets from entering images,
- image labels include version/commit when available.

## Configuration Model

Use environment variables and typed settings for:

- database URL,
- Kafka bootstrap servers and topic/group settings,
- Qdrant URL/API key if applicable,
- object storage endpoint/bucket/credentials,
- secret store mode,
- OpenTelemetry/exporter config,
- feature flags,
- worker role,
- log level,
- dev workbench flag,
- deterministic vs real embedding provider,
- connector rollout flags.

Missing required dependencies should fail readiness clearly, not crash with
opaque stack traces. Optional dependencies should degrade explicitly.

## Health And Readiness

API endpoints:

- `GET /health/live`: process is alive.
- `GET /health/ready`: required dependencies are reachable and migrations are
  compatible.

Worker health:

- worker heartbeat records,
- role name,
- instance ID,
- last heartbeat,
- current lease/job summary where safe,
- readiness failure reason when dependency is missing.

Readiness should check only what the service needs. For example, a retrieval
worker should not require connector credentials to be ready.

## Migration Strategy

Migrations should run as an explicit operation, not as an implicit API startup
side effect.

Phase 12 should provide:

- a containerized migration command,
- an optional Compose `migrate` service/profile,
- hosted-container docs explaining when to run migrations,
- readiness behavior that reports incompatible or missing schema clearly.

API and worker containers should not auto-run migrations on normal startup.

## Docker Compose Stack

Compose should support:

- API,
- at least one worker role,
- Postgres,
- Apache Kafka,
- Qdrant,
- MinIO object storage,
- optional Redis,
- local environment defaults.

Compose validation:

- API starts,
- migration command/service succeeds,
- migrations can run,
- at least one worker role starts,
- Kafka topic/consumer smoke works,
- Qdrant health works,
- MinIO/object storage health works,
- `/health/live` and `/health/ready` behave correctly.

Compose services should include healthchecks where practical for Postgres,
Kafka, Qdrant, MinIO, API readiness, and worker heartbeat/smoke. `depends_on`
alone is not sufficient proof that the stack is usable.

Do not require real Slack/Linear/GitHub/Grafana/OpenAI credentials for the base
Compose smoke. Use deterministic/local modes by default.

## Simple Hosted Containers

Document beta deployment assumptions:

- managed Postgres,
- managed or hosted Apache Kafka-compatible operational equivalent only if
  explicit; local validation remains Apache Kafka,
- managed object storage,
- managed Qdrant or containerized Qdrant depending on beta host,
- Grafana Cloud for observability,
- managed ingress/TLS/reverse proxy outside Cortex containers.

Docs should state which environment variables are required, which secrets are
provider credentials, which services are stateful, and which services can scale
horizontally.

## Kubernetes-Compatible Boundaries

Document but do not implement required Kubernetes manifests:

- stateless API can scale horizontally,
- workers scale horizontally by role and Kafka consumer group,
- Postgres/object storage/Qdrant/Kafka are stateful dependencies,
- readiness/liveness map cleanly to probes,
- worker heartbeats map to operational health,
- config/secrets map to env/secret volumes later,
- no singleton custom leader; use Kafka consumer groups and Postgres leases.

## Acceptance Criteria

Phase 12 is complete when:

- API and worker images build reproducibly,
- container builds use pinned dependencies and guarded build context,
- Docker Compose starts API, at least one worker, Postgres, Apache Kafka,
  Qdrant, and MinIO/object storage,
- base Compose smoke requires no real provider/model/Grafana credentials,
- migrations run through an explicit containerized command/service,
- current `pipeline` and `noop` worker roles can run independently,
- API health/readiness fail clearly when dependencies are missing,
- worker heartbeat records show role/instance/readiness,
- deployment docs list required env vars and secret boundaries,
- docs state which services can scale horizontally,
- Kubernetes-compatible boundaries are documented without requiring Kubernetes.
