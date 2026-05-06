# ADR-015: Rate Limits Backpressure And Repair

## Status

Accepted.

## Decision

Track provider rate limits, worker leases, backpressure, deadletters, and repair
jobs from the first connector.

## What It Is

Cortex records rate-limit buckets, retry-after windows, cursor state, worker
heartbeats, worker leases, Kafka lag, failed events, deadletters, and repair
jobs for replay/re-normalization/re-chunking/re-embedding/re-indexing.

## Why Cortex Uses It

- Slack/GitHub/Linear APIs have rate limits and transient failures.
- Backfills can overload provider APIs or internal workers.
- Replayability is only useful if repair workflows exist.

## Alternatives Considered

- Simple retries only.
- Manual replay only.
- Add rate-limit tracking after scale.

## Why Alternatives Lost

- Simple retries can hammer providers and lose cursor correctness.
- Manual-only repair is too brittle for design-partner data.
- Adding this later risks rewrites around connector and worker state.

## Tradeoffs

- More job/worker state in Postgres.
- More operational UI/CLI surface area.
- Workers need lease and heartbeat discipline.

## Failure Modes

- Workers continue after lease expiry and double-process events.
- Provider retry-after ignored during backfills.
- Deadletters lack enough context to replay safely.

## How We Test It

- Retry-after pauses/reschedules jobs.
- Worker lease expiry releases work safely.
- Deadletter records include reason, replay hint, attempts, and source context.
- Repair jobs rebuild derived state from raw events.

## How This Maps From CortexG

`cortexg` already models sync jobs, cursors, worker runs, leases, rate-limit
buckets, and deadletters. Cortex keeps those concepts in the Python/Kafka
architecture.

