# Render demo deployment

`render.yaml` provisions one free, Docker-based FastAPI web service for the
deterministic Cortex demo. It is the Render equivalent of the API half of the
Vercel + Railway demo; it is not a durable production topology.

## Deploy

1. In Render, create a new **Blueprint** and select this repository.
2. Render detects `render.yaml`, builds the root `Dockerfile`, and creates the
   `cortex-api-demo` web service.
3. Leave the committed demo variables in place. The Docker command binds
   Uvicorn to Render's injected `$PORT`; Render probes `/health/live`.
4. After the service is live, copy its `https://<service>.onrender.com` URL.
5. Set the frontend's server-only `CORTEX_API_ORIGIN` variable in Vercel to
   that URL, then redeploy the frontend.

Verify the deployment:

```text
GET https://<service>.onrender.com/health/live
GET https://<vercel-domain>/api/cortex/health/live
```

## Demo boundary

The Blueprint deliberately uses `CORTEX_STATE_BACKEND=memory` and
`CORTEX_EVENT_BUS=memory`, with the local fixture workbench disabled. Render's
free service can spin down and has no durable demo-state guarantee. Do not
enable live connectors, OAuth callbacks, or provider credentials on this
service.

## Environment variables and secrets

The committed Blueprint contains only non-secret demo settings. If a future
deployment enables SQL state, Kafka, a connector, or observability, add its
credential variables in the Render Dashboard (or as `sync: false` placeholders
in a separate Blueprint) rather than committing values. This includes
`DATABASE_URL`, `CORTEX_SECRET_ENCRYPTION_KEY`, provider tokens, webhook
secrets, and `OTEL_EXPORTER_OTLP_ENDPOINT`.

That future deployment also requires the managed dependencies and separate
worker topology described in [hosted-containers.md](hosted-containers.md); it
must not reuse this free, single-service demo configuration.
