# ADR-011: Slack Files And Diagrams Via Metadata And OCR

## Status

Accepted.

## Decision

Treat Slack files, diagrams, and images as first-class source files in v1. Store
metadata and OCR text first; defer deeper vision-model diagram understanding.

## What It Is

Slack files/images are captured as source files with provider metadata, object
storage location, MIME type, size, filename, Slack permalink, thread/message
references, and OCR text when possible.

## Why Cortex Uses It

- The user specifically needs to find old diagrams and scattered context.
- Metadata plus OCR solves a large part of diagram discoverability cheaply.
- Deep vision reasoning is more expensive and harder to evaluate.

## Alternatives Considered

- Metadata only.
- Vision extraction from day one.

## Why Alternatives Lost

- Metadata only is too weak for diagram retrieval.
- Vision extraction v1 adds cost, latency, model variance, and eval complexity.

## Tradeoffs

- OCR may miss visual structure.
- Diagrams without text may remain weakly searchable.
- Vision summarization will likely be needed later for higher quality.

## Failure Modes

- Files expire or cannot be downloaded after Slack token/scope changes.
- OCR text can be inaccurate.
- Sensitive filenames/OCR text must respect source allowlists.

## How We Test It

- Slack file ingestion fixtures.
- OCR text extraction fixtures.
- Retrieval by filename, caption, thread context, and OCR text.
- Allowlist tests for file metadata and OCR snippets.

## How This Maps From CortexG

`cortexg` models source objects/chunks but does not deeply productionize
multimodal Slack files. Cortex makes source files explicit.

