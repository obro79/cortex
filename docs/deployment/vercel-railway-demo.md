# Vercel + Railway demo deployment

This deployment shape is intentionally for the deterministic Cortex demo. It
does not claim the durable Kafka/Qdrant pipeline is production-ready.

## Topology

```text
Browser → Vercel Next.js frontend → server-only BFF → Railway FastAPI API
                                                    → Railway Postgres
```

The Vercel BFF uses `CORTEX_API_ORIGIN`; it is server-only and must never use a
`NEXT_PUBLIC_` prefix. The browser calls only `/api/cortex/*`.

## Railway API service

Create a Railway project from this repository and attach a Railway Postgres
service. The committed `railway.toml` starts the FastAPI API and uses
`/health/live` for deployment health checks.

Set these Railway variables:

```text
CORTEX_ENV=staging
CORTEX_LOG_LEVEL=INFO
CORTEX_STATE_BACKEND=memory
CORTEX_EVENT_BUS=memory
CORTEX_DEV_WORKBENCH_ENABLED=false
DATABASE_URL=${{Postgres.DATABASE_URL}}
```

Use one API replica. Keep all connector credentials disabled unless a connector
is explicitly being demonstrated. The local fixture workbench deliberately
remains unavailable outside `local` and `test`; do not expose its seed/reset
routes through a public demo deployment.

## Vercel frontend

Import the same GitHub repository into Vercel with **Root Directory** set to
`frontend`. Vercel uses `frontend/vercel.json` and the lockfile to build Next.js.

Set this Vercel variable for Preview and Production:

```text
CORTEX_API_ORIGIN=https://<railway-api-domain>
```

After deployment, verify:

```text
GET https://<railway-api-domain>/health/live
GET https://<vercel-domain>/api/cortex/health/live
```

## Durable production follow-up

Before calling this a production deployment, add managed Kafka, shared object
storage, managed Qdrant, a separate Railway pipeline-worker service, explicit
migrations, and environment-specific retention/observability. Do not point a
worker at local file payload storage shared only by the API container.
