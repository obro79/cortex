# ADR-007: Source-Aware Chunking

## Status

Accepted.

## Decision

Use source-aware, versioned chunking rather than uniform chunk splitting.

## What It Is

Each source type produces chunks that preserve its natural structure: Slack
threads/messages, Linear issue overviews/comments, GitHub PR overviews/reviews,
doc sections, agent session segments, and Slack file/OCR chunks.

## Why Cortex Uses It

- Citations are clearer when chunks map to source-native objects.
- Engineering retrieval benefits from preserving thread, issue, PR, and file
  context.
- Chunking versions allow safe rebuilds and embedding migrations.

## Alternatives Considered

- Uniform small chunks.
- Generic semantic splitter.

## Why Alternatives Lost

- Uniform chunks lose source structure and create noisy citations.
- Generic semantic splitting can be useful later but should not replace
  source-native chunk boundaries in v1.

## Tradeoffs

- More source-specific code.
- Chunking requires per-source tests and tuning.
- Rechunking requires embedding/index rebuilds.

## Failure Modes

- Chunks that are too large waste retrieval budget.
- Chunks that are too small lose decision rationale.
- Missing chunking versions can mix incompatible embeddings.

## How We Test It

- Snapshot tests for each source chunk type.
- Token budget tests.
- Citation integrity tests.
- Retrieval evals before/after chunking changes.

## How This Maps From CortexG

`cortexg` already has a good source-aware chunker. Cortex should port the
strategy conceptually and make it versioned/configurable in Python.

