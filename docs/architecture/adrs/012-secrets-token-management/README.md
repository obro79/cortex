# ADR-012: Secrets And Token Management

## Status

Accepted.

## Decision

Store OAuth tokens, provider credentials, and local MCP session secrets through
secret references with encryption and rotation metadata. Do not store raw token
material in ordinary application tables.

## What It Is

`SecretRef` records point to encrypted secret material in a managed secrets
service or encrypted secret store. Application tables store metadata: provider,
workspace, scopes, status, expiry, key version, rotation status, and audit
links.

## Why Cortex Uses It

- Cortex connects to Slack, Linear, GitHub, and model providers.
- Hosted-first architecture raises the bar for token handling.
- Token metadata is needed for health, reauth, scope drift, and audit without
  exposing raw secrets.

## Alternatives Considered

- Raw encrypted token columns in Postgres.
- Environment variables per workspace.
- User-managed local tokens only.

## Why Alternatives Lost

- Raw DB token columns increase blast radius.
- Per-workspace env vars do not scale.
- Local-only tokens conflict with hosted ingestion and webhooks.

## Tradeoffs

- Requires secret-store integration earlier.
- Local development needs a simple encrypted fallback.
- Rotation and reauthorization states add product complexity.

## Failure Modes

- Token leakage through logs or debug output.
- Scope drift after provider-side app changes.
- Expired/revoked tokens causing silent connector staleness.

## How We Test It

- Secret material never appears in API responses, logs, or audit payloads.
- Expired/revoked token states mark connectors unhealthy.
- Rotation preserves source connection identity.
- Local development fallback is clearly separated from production storage.

## How This Maps From CortexG

`cortexg` has connector metadata and environment-token assumptions. Cortex makes
secret references a first-class production contract.

