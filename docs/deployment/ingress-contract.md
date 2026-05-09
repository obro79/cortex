# Ingress Contract

Cortex expects a managed ingress or reverse proxy in front of the API. The app
does not implement a custom ingress controller.

## Required Behavior

- Terminate TLS before requests reach the API container.
- Forward `X-Forwarded-For`, `X-Forwarded-Proto`, and request IDs.
- Route `/health/live` and `/health/ready` directly to the API service.
- Enforce request body limits before requests reach connector webhooks.
- Use compression only for safe response types and never for secrets.
- Apply idle and request timeouts long enough for connector OAuth callbacks and
  webhook ingestion, but short enough to avoid stuck clients.
- Load-balance only across healthy API instances.

## App Assumptions

- Liveness remains unauthenticated and lightweight.
- Readiness may return `503` with sanitized config issue codes.
- Rate-limit middleware exempts health paths.
- API responses, health checks, logs, and metrics must not include OAuth tokens,
  raw Slack payloads, private file URLs, or source snippets.
- Public ingress should route only API paths; internal support operations remain
  service-internal, permission-gated, and audited.

## Suggested Limits

- Request body size: start at 2 MiB for API requests and configure explicit
  larger limits only for known connector webhook needs.
- Request timeout: start at 30 seconds for normal API paths.
- Idle timeout: start at 60 seconds.
- Health timeout: 5 seconds or less.

Environment-specific ingress files can use different syntax, but must preserve
these behavioral guarantees.
