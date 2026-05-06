# ADR-013: Webhook Security And Idempotency

## Status

Accepted.

## Decision

Verify provider webhook signatures before ingestion and persist delivery
idempotency records before publishing Kafka events.

## What It Is

`WebhookDelivery` records capture provider, delivery ID, signature verification
result, idempotency key, source connection, status, attempts, and processing
timestamps.

## Why Cortex Uses It

- Providers retry webhook deliveries.
- Webhooks are a public ingress path and must reject forged payloads.
- Duplicate deliveries must not create duplicate raw events, chunks, or
  embeddings.

## Alternatives Considered

- Trust provider webhook URLs without signature checks.
- Deduplicate only at raw event normalization.
- Ignore duplicate deliveries and rely on downstream idempotency.

## Why Alternatives Lost

- Unsigned webhooks are unsafe for production.
- Downstream-only dedupe makes observability and replay harder.
- Duplicate raw events can inflate costs and pollute retrieval.

## Tradeoffs

- Provider-specific signature logic is needed.
- Delivery records add storage and operational surfaces.
- Clock skew and provider retries need careful handling.

## Failure Modes

- Valid webhooks rejected due to timestamp/signature bugs.
- Duplicate deliveries race before idempotency record commit.
- Partial failures after delivery record creation but before Kafka publication.

## How We Test It

- Signature verification fixtures per provider.
- Duplicate delivery tests.
- Partial failure/retry tests.
- Idempotency tests across webhook, raw event, and Kafka publish paths.

## How This Maps From CortexG

`cortexg` models raw events and sync jobs. Cortex adds production webhook ingress
security and delivery idempotency before raw events are queued.

