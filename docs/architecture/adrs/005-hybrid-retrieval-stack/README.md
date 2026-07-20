# ADR-005: Hybrid Retrieval Stack

## Status

Accepted.

## Decision

Use hybrid retrieval: Postgres full-text search plus Qdrant in v1, with an
OpenSearch adapter added when lexical scale or filtering requires it.

## What It Is

Hybrid retrieval combines lexical search, vector search, relationship expansion,
source-aware ranking, and optional reranking to produce cited evidence packs.

## Why Cortex Uses It

- Engineering context often depends on exact identifiers: issue IDs, PR numbers,
  file paths, function names, commit SHAs, and diagram filenames.
- Semantic vector search helps find related decisions when wording differs.
- Qdrant is a focused vector database with a cheap path.
- Postgres full-text keeps early cost lower than running OpenSearch immediately.

## Alternatives Considered

- Postgres + pgvector only.
- OpenSearch + Qdrant from day one.
- Vector-only retrieval.

## Why Alternatives Lost

- pgvector-only is simpler but weaker for hybrid retrieval and index evolution.
- OpenSearch from day one is architecturally strong but can be a cost/ops
  pressure point.
- Vector-only misses exact engineering identifiers too often.

## Tradeoffs

- Two retrieval paths must be merged and evaluated.
- Qdrant index freshness must be monitored.
- OpenSearch migration should be planned behind an adapter.

## Failure Modes

- Vector results can retrieve semantically similar but stale decisions.
- Lexical search can miss paraphrased Slack context.
- Index lag can produce incomplete context gate decisions.

## How We Test It

- Golden retrieval queries across Slack, Linear, GitHub, and docs.
- Exact identifier tests for issue IDs, PRs, SHAs, and file paths.
- Semantic recall tests for paraphrased architecture decisions.
- Index freshness/source coverage tests.

## Configuration And Tuning

Retrieval knobs are versioned configuration, not scattered constants. Chunk
sizes, overlap, embedding model/dimensions, candidate limits, ranking weights,
gate thresholds, and token budgets are defined in
[`config-and-tuning.md`](config-and-tuning.md).

## Hosted Indexing Decision

The durable deployment target uses hosted Qdrant while local development uses a
persistent Compose instance. Qdrant remains a content-free, rebuildable derived
index; Postgres is canonical. See
[ADR-005.1: Hosted Qdrant as a Derived Vector Index](child-adrs/001-hosted-qdrant-derived-index.md).

## How This Maps From CortexG

`cortexg` has deterministic scoring plus optional embeddings. Cortex keeps the
scoring dimensions but moves retrieval into real lexical/vector indexes.
