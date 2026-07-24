# ADR 007 — Migrate retrieval embeddings to Gemini Embedding 2

**Status:** Accepted
**Date:** 2026-07-23

## Context

Cortex previously used `gemini-embedding-001` with the API `taskType` field.
The current Gemini API exposes `gemini-embedding-2`, which supports text and
multimodal content in one space. Google documents two migration constraints:

- the Embedding 1 and Embedding 2 vector spaces are incompatible;
- Embedding 2 does not accept `task_type`; asymmetric retrieval intent belongs
  in the text instruction.

## Decision

- Production model: `gemini-embedding-2`.
- Output dimensions: 1536.
- Embedding version: `gemini2-1536-v1`.
- Document prefix: `title: none | text: {content}`.
- Query prefix: `task: search result | query: {query}`.
- Qdrant collection identity includes model, version, and dimensions.
- Existing Embedding 1 points are never queried together with Embedding 2.
- Demo and production corpora must be re-embedded into the new collection.
- `GEMINI_API_KEY` remains a runtime secret and is never accepted through an
  API, MCP argument, fixture, log, or report.

## Consequences

- The migration creates a new collection rather than mutating the old one.
- Rollout requires complete re-indexing before switching retrieval traffic.
- Rollback selects the previous collection/profile; it does not translate
  vectors.
- Multimodal inputs can be added later without another model family, but this
  slice remains text-only.

## Verification

- Provider tests assert the Embedding 2 URL and absence of `taskType`.
- Document/query tests assert the exact asymmetric prefixes.
- Profile tests assert a distinct
  `...gemini-embedding-2-gemini2-1536-v1-1536` collection.
- A credentialed smoke test is still required before claiming live Gemini
  embeddings.

## References

- [Gemini Embedding 2 model](https://ai.google.dev/gemini-api/docs/models/gemini-embedding-2)
- [Gemini API embeddings and migration](https://ai.google.dev/gemini-api/docs/embeddings)
