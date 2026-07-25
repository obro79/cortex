# ADR-022: Apache Kafka Runtime

## Status

Accepted.

## Decision

Use Apache Kafka as the concrete runtime for Cortex pipeline events.

Local development uses the official JVM Apache Kafka Docker image in KRaft mode:
`apache/kafka:4.2.0`.

## What It Is

ADR-002 chose Kafka as the event backbone. This ADR narrows the implementation:
Cortex validates against real Apache Kafka, not a Kafka-compatible substitute.

KRaft mode removes the ZooKeeper dependency for local and early hosted
deployments.

## Why Cortex Uses It

- Real Kafka behavior matters for partitioning, offset commits, lag, and
  consumer group semantics.
- Avoiding compatibility substitutes reduces surprises before production.
- KRaft keeps the local stack small while still exercising Apache Kafka.

## Alternatives Considered

- Redpanda.
- Confluent Kafka images.
- External Kafka only.
- Apache `kafka-native`.

## Why Alternatives Lost

- Redpanda is simpler locally but is Kafka-compatible rather than Apache Kafka.
- Confluent Kafka is real Kafka but adds vendor-specific packaging and a heavier
  local stack than this phase needs.
- External Kafka only would make local and CI smoke tests harder to reproduce.
- Apache marks `kafka-native` experimental, so Cortex uses the JVM image.

## Tradeoffs

- Apache Kafka is heavier locally than Redpanda.
- KRaft-only local deployment is not the same as a multi-broker production
  cluster.
- Docker Compose needs explicit listener configuration for host and container
  clients.

## How We Test It

- Unit tests cover topic mapping, producer serialization, and consumer dispatch.
- Optional smoke tests run against `KAFKA_BOOTSTRAP_SERVERS`.
- Docker Compose starts a single-node Kafka broker for local validation.

## How This Maps From CortexG

`cortexg` had queue abstractions. Cortex keeps the event abstraction but
standardizes the runtime on Apache Kafka.
