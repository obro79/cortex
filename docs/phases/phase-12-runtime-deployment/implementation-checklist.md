# Phase 12 Implementation Checklist

## 1. Container Build Foundations

- Add API Dockerfile or target.
- Add worker Dockerfile or target.
- Ensure deterministic dependency install from a lockfile or another pinned
  dependency source.
- Run as non-root where practical.
- Add image labels for version/commit when available.
- Ensure secrets are not baked into images.
- Add `.dockerignore` or build-context guardrails for local env files, run logs,
  payload stores, caches, and secrets.

Acceptance:

- API image builds,
- worker image builds,
- image scan/check confirms no known project secrets in layers,
- build context excludes local secrets and run artifacts.

Commit:

- `phase 12: add container build foundations`

## 2. Runtime Entrypoints

- Confirm API entrypoint works in container.
- Confirm worker command supports current independent `--role` values:
  `pipeline` and `noop`.
- Add role env/command examples.
- Ensure workers exit clearly on invalid role/config.
- Document future worker role boundaries separately from currently supported
  CLI roles.

Acceptance:

- current `pipeline` and `noop` roles can start independently,
- invalid role produces clear error.

Commit:

- `phase 12: add runtime entrypoints`

## 3. Configuration Model

- Document required env vars.
- Add typed settings validation where missing.
- Separate required and optional dependencies.
- Add deterministic/local defaults for Compose.
- Ensure missing required config produces actionable readiness errors.

Acceptance:

- settings tests cover required/missing/optional config,
- base local Compose does not require real provider credentials.

Commit:

- `phase 12: add deployment configuration`

## 4. Health, Readiness, And Heartbeats

- Harden `GET /health/live`.
- Harden `GET /health/ready`.
- Add dependency checks for DB, Kafka, Qdrant, and object storage where needed.
- Add worker heartbeat records.
- Add worker readiness failure reasons.
- Add Compose-level healthchecks where practical for Postgres, Kafka, Qdrant,
  MinIO, API readiness, and worker heartbeat/smoke.

Acceptance:

- readiness fails clearly when a required dependency is missing,
- worker heartbeats include role, instance, timestamp, and safe status.

Commit:

- `phase 12: add health and worker readiness`

## 5. Docker Compose Local Stack

- Add Compose services for API and at least one worker.
- Add Postgres.
- Add Apache Kafka KRaft service using `apache/kafka:4.2.0`.
- Add Qdrant.
- Add MinIO object storage.
- Add optional `migrate` service/profile or documented containerized migration
  command.
- Add optional Redis only if needed by existing code paths.
- Add named volumes and local env examples.

Acceptance:

- `docker compose up` starts the base stack,
- explicit migration command/service runs successfully,
- API and worker can communicate with dependencies,
- no real provider/model/Grafana credentials required.

Commit:

- `phase 12: add Docker Compose stack`

## 6. Containerized Smoke Tests

- Add migration smoke.
- Add API health/readiness smoke.
- Add worker startup smoke.
- Add Kafka producer/consumer or pipeline smoke.
- Add Qdrant health smoke.
- Add object storage health smoke.
- Add Compose healthcheck validation where practical.

Acceptance:

- smoke script exits nonzero on failure,
- failures point to the missing dependency/config.

Commit:

- `phase 12: add deployment smoke tests`

## 7. Hosted Container Deployment Docs

- Document required services.
- Document env vars and secret boundaries.
- Document startup order.
- Document migration command.
- Document that API/worker startup does not auto-run migrations.
- Document scaling assumptions by service.
- Document observability config.

Acceptance:

- docs are enough to deploy simple hosted containers without Kubernetes,
- docs state which services are stateful and which scale horizontally.

Commit:

- `phase 12: document hosted container deployment`

## 8. Kubernetes-Compatible Boundary Docs

- Document future probe mapping.
- Document future secret/config mapping.
- Document worker scaling by Kafka consumer groups.
- Document stateful dependency boundaries.
- Document what is intentionally not Kubernetes yet.

Acceptance:

- Kubernetes-compatible service boundaries are clear,
- no Kubernetes manifests are required for Phase 12 completion.

Commit:

- `phase 12: document Kubernetes-compatible boundaries`

## Commit Cadence

Use separate commits:

1. Container build foundations.
2. Runtime entrypoints.
3. Deployment configuration.
4. Health/readiness/heartbeats.
5. Docker Compose stack.
6. Deployment smoke tests.
7. Hosted container docs.
8. Kubernetes-compatible boundary docs.

Keep runtime packaging changes separate from docs-only deployment assumptions so
failures are easy to isolate.
