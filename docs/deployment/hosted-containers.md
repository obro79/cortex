# Hosted Container Deployment

Phase 12 supports simple hosted-container beta deployments. Kubernetes is not
required for this phase.

## Services

Stateless Cortex services:

- `api`: FastAPI HTTP service for API, OAuth callbacks, MCP/API endpoints, and
  health/readiness.
- `worker-pipeline`: Kafka pipeline worker using `cortex-worker --role
  pipeline`.
- `worker-noop`: smoke role using `cortex-worker --role noop`.
- `migrate`: explicit one-shot migration command using `alembic upgrade head`.

Stateful dependencies:

- managed Postgres,
- Apache Kafka or an explicitly selected Kafka-compatible managed service,
- object storage compatible with the Cortex payload/file storage boundary,
- Qdrant, managed or containerized,
- Grafana Cloud for observability exports.

## Startup Order

1. Provision Postgres, Kafka, object storage, and Qdrant.
2. Build/publish the `api` and `worker` image targets.
3. Run migrations explicitly:

   ```bash
   docker compose --profile migrate run --rm migrate
   ```

4. Start `api`.
5. Start `worker-pipeline`.
6. Verify `/health/live`, `/health/ready`, worker startup logs, and Kafka topic
   creation.

API and worker startup must not run migrations implicitly.

## Required Environment

Required for SQL/Kafka runtime:

- `CORTEX_STATE_BACKEND=sql`
- `CORTEX_EVENT_BUS=kafka`
- `DATABASE_URL`
- `KAFKA_BOOTSTRAP_SERVERS`
- `KAFKA_CONSUMER_GROUP`
- `PAYLOAD_STORE_PATH` for local file payload storage, or object-storage config
  once that backend is enabled.

Operational environment:

- `CORTEX_ENV`
- `CORTEX_LOG_LEVEL`
- `CORTEX_SERVICE_NAME`
- `CORTEX_OTEL_ENABLED`
- `OTEL_EXPORTER_OTLP_ENDPOINT`

Optional source rollout flags:

- `CORTEX_SLACK_CONNECTOR_ENABLED`
- `CORTEX_LINEAR_CONNECTOR_ENABLED`
- `CORTEX_GITHUB_CONNECTOR_ENABLED`
- `CORTEX_REPO_DOCS_CONNECTOR_ENABLED`
- `CORTEX_DEV_WORKBENCH_ENABLED`

## Secret Boundaries

Provider and infrastructure secrets are runtime environment or managed secret
values only. Do not bake them into images, docs, dashboards, or committed run
logs.

Secrets include:

- Slack client secret and signing secret,
- Linear API token,
- GitHub app private key, webhook secret, and installation token,
- database credentials,
- Kafka credentials if using a managed authenticated cluster,
- object storage credentials,
- Qdrant API key when configured,
- OTLP exporter credentials when required by the host.

Health, readiness, logs, metrics, and smoke output must use statuses, hashes,
counts, role names, service names, and sanitized error codes rather than raw
secrets or source content.

## Scaling

Horizontally scalable:

- `api`: stateless; scale behind managed ingress/load balancing.
- `worker-pipeline`: scale by Kafka consumer group membership.
- future worker roles: scale independently by role and consumer group.

Stateful or managed:

- Postgres,
- Kafka,
- object storage,
- Qdrant,
- Grafana Cloud.

Do not add a custom singleton leader. Prefer Kafka consumer groups, Postgres
leases where needed, and idempotent pipeline records.

## Local Smoke

Cheap validation:

```bash
python scripts/deployment_smoke.py --no-build
```

Build validation:

```bash
python scripts/deployment_smoke.py
```

Full local stack validation:

```bash
python scripts/deployment_smoke.py --full
```
