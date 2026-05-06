# ADR-008: Deterministic-First Linking

## Status

Accepted.

## Decision

Build relationships with deterministic links first, then add AI-suggested
candidate links with confidence and citations.

## What It Is

Linking connects Slack threads, Linear issues, GitHub PRs/commits, docs, files,
people, and code paths so retrieval can expand from a task to related context.

## Why Cortex Uses It

- Deterministic links are explainable and auditable.
- Engineering sources contain many reliable identifiers: URLs, issue IDs, PR
  numbers, commit SHAs, branch names, file paths, Slack permalinks, and users.
- AI linking can improve recall but should not be the only source of truth.

## Alternatives Considered

- AI-first linking.
- Deterministic-only linking.

## Why Alternatives Lost

- AI-first links are harder to trust, debug, and evaluate.
- Deterministic-only misses implicit architecture relationships buried in
  discussion.

## Tradeoffs

- Two-stage linking adds pipeline complexity.
- AI candidate links need confidence thresholds and review/eval loops.
- Deterministic parsing must handle provider-specific URL/id formats.

## Failure Modes

- False semantic links can pollute retrieval.
- Missing deterministic parsers can hide obvious relationships.
- Identity mapping errors can link the wrong people or repos.

## How We Test It

- URL/ID/path parser tests.
- Relationship inference fixtures.
- Retrieval expansion tests.
- AI candidate threshold/eval tests before enabling broad semantic linking.

## How This Maps From CortexG

`cortexg` has a `source_relationships` model and retrieval relationship boost.
Cortex makes relationship creation a first-class pipeline stage.

