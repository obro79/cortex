# ADR-016: Retrieval Evals And Model Gateway

## Status

Accepted.

## Decision

Build retrieval eval logging and a model gateway into v1. Use evals to compare
embedding providers, dimensions, retrieval strategies, reranking, and context
gate behavior.

## What It Is

The model gateway centralizes embeddings, extraction, OCR, reranking, and answer
synthesis calls. Retrieval evals define golden queries, expected evidence,
expected gate status, permission expectations, and quality metrics.

## Why Cortex Uses It

- Retrieval quality is the product.
- Provider-neutral embeddings require benchmarks, not opinions.
- Cost and latency must be visible per workspace and task type.
- Context gates need measurable allow/warn/block accuracy.

## Alternatives Considered

- Tune retrieval manually.
- Pick Gemini and skip provider comparisons.
- Add evals after product usage.

## Why Alternatives Lost

- Manual tuning does not scale or prove quality.
- A strong default model can still underperform on Cortex-specific Slack/PR/docs
  data.
- Waiting on evals delays the feedback loop that makes retrieval accurate.

## Tradeoffs

- Eval fixtures take time to curate.
- Model gateway adds an abstraction layer.
- Quality metrics can create false confidence if fixtures are too narrow.

## Failure Modes

- Evals overfit to demo fixtures.
- Model gateway hides provider-specific failure semantics.
- Cost logging misses retries or large OCR/extraction calls.

## How We Test It

- Golden retrieval cases track Recall@K, MRR, citation accuracy, conflict
  detection, gate accuracy, permission safety, latency, and token efficiency.
- Compare Postgres FTS only, Qdrant only, hybrid, hybrid + relationships, hybrid
  + reranking.
- Compare Gemini 1536, Gemini 3072, and OpenAI embedding candidates.
- Model invocation logs record provider, model, task, input size, latency, cost
  estimate, retries, status, and error.

## How This Maps From CortexG

`cortexg` has retrieval eval foundations and deterministic demo embeddings.
Cortex turns evals and model invocation records into core production contracts.

