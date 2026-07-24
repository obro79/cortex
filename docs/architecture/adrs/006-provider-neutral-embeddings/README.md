# ADR-006: Provider-Neutral Embeddings

## Status

Accepted.

## Decision

Implement embeddings behind a provider-neutral interface. Use Google
`gemini-embedding-2` at 1536 dimensions as the current default, with OpenAI and
other providers supported by adapter.

## What It Is

Embedding workers turn source chunks into vectors for semantic retrieval. Each
embedding record stores provider, model, dimensions, task type, chunking version,
retrieval index version, content hash, vector hash, status, and error state.

## Why Cortex Uses It

- The user wants provider neutrality.
- Gemini embeddings are a strong default, but model quality should be validated
  with Cortex-specific retrieval evals.
- Provider abstraction prevents schema lock-in.
- Model/dimension/version metadata enables re-embedding and index migration.

## Alternatives Considered

- Gemini-only.
- OpenAI-only.
- No default provider.
- Fine-tuned embeddings in v1.

## Why Alternatives Lost

- Single-provider designs create avoidable lock-in.
- No default makes developer experience worse.
- Fine-tuning is premature before retrieval failure data exists.

## Tradeoffs

- Provider abstraction adds adapter/test surface.
- Different providers have different batching, dimensions, auth, and task-type
  semantics.
- Running evals is required before changing defaults confidently.

## Failure Modes

- Embedding dimension mismatch can corrupt vector indexes.
- Re-embedding without versioning can mix incompatible vectors.
- Provider rate limits can stall indexing.

## How We Test It

- Adapter contract tests.
- Dimension/hash validation tests.
- Re-embedding lifecycle tests.
- Retrieval evals comparing Gemini 1536, Gemini 3072, and OpenAI candidates.

## How This Maps From CortexG

`cortexg` has an embedding provider interface and lifecycle. Cortex keeps that
shape, changes the default to Gemini, and makes provider neutrality explicit.
