# Phase 12 Test Plan

## Commands

```bash
ruff check .
ruff format --check .
mypy src
pytest
docker compose config
```

Focused local loop:

```bash
pytest tests/api/test_health.py tests/workers tests/config tests/deployment
```

Container smoke:

```bash
docker compose up -d postgres kafka qdrant minio api worker
docker compose ps
```

## Coverage Map

```txt
Images
  -> API image builds
  -> worker image builds
  -> pinned dependency install
  -> no baked secrets
  -> build context excludes local secrets

Entrypoints
  -> API starts
  -> current pipeline/noop worker roles start independently
  -> invalid role fails clearly

Config
  -> required env validation
  -> optional dependency degradation
  -> deterministic local defaults

Health
  -> liveness
  -> readiness
  -> dependency missing failures
  -> worker heartbeats

Compose
  -> Postgres
  -> Apache Kafka KRaft
  -> Qdrant
  -> MinIO object storage
  -> API
  -> worker
  -> migrate command/service

Docs
  -> hosted container env vars
  -> secret boundaries
  -> horizontal scaling
  -> Kubernetes-compatible boundaries
```

## Tests To Create

| Test file | Assertions |
| --- | --- |
| `tests/deployment/test_settings.py` | Required/missing env vars, optional dependencies, deterministic local defaults. |
| `tests/deployment/test_container_commands.py` | API/worker commands and invalid worker role behavior. |
| `tests/deployment/test_migration_command.py` | Containerized migration command/service runs explicitly and API startup does not auto-migrate. |
| `tests/api/test_health_readiness.py` | Liveness/readiness pass/fail with dependency checks. |
| `tests/workers/test_worker_heartbeats.py` | Worker role, instance ID, heartbeat timestamp, safe status. |
| `tests/deployment/test_compose_config.py` | Compose config contains API, worker, Postgres, Apache Kafka, Qdrant, MinIO, and migrate command/service. |
| `tests/deployment/test_compose_healthchecks.py` | Compose services define healthchecks where practical and do not rely only on `depends_on`. |
| `tests/deployment/test_secret_boundaries.py` | Images/config examples/build context do not contain provider tokens, secrets, env files, run logs, or payload stores. |
| `tests/deployment/test_scaling_docs.py` | Deployment docs name horizontally scalable and stateful services. |

## Smoke Matrix

| Smoke | Expected behavior |
| --- | --- |
| API image build | Image builds without secrets. |
| Worker image build | Image builds and exposes role command. |
| Compose config | Valid compose file. |
| Compose start | API, worker, Postgres, Kafka, Qdrant, object storage healthy or clearly failing. |
| Migration | Explicit Alembic migration command/service runs against Compose Postgres. |
| API live | `/health/live` returns live. |
| API ready | `/health/ready` succeeds when dependencies exist and fails clearly when missing. |
| Worker heartbeat | Current `pipeline`/`noop` worker roles write heartbeat or pass smoke with role/instance/status. |
| Kafka smoke | Producer/consumer or pipeline smoke succeeds. |
| Qdrant/object storage smoke | Health checks succeed. |

## Failure Assertions

Simulate:

- missing `DATABASE_URL`,
- Kafka unavailable,
- Qdrant unavailable for worker needing vector index,
- MinIO/object storage unavailable for connector/file path,
- invalid worker role,
- missing migration or incompatible schema.

Expected result: readiness or startup fails with a clear sanitized reason and no
secret leakage.

## Not Required In Phase 12

- Kubernetes manifests,
- production autoscaling,
- full backup/restore implementation,
- public admin UI,
- new source connectors,
- Phase 13 platform components.
