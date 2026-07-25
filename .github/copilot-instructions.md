# Cortex Copilot Review Instructions

Review Cortex as a production-shaped Python/FastAPI backend. Prioritize bugs,
security risks, contract drift, and missing tests over style-only comments.

Key review priorities:

- `/dev/*` routes must stay disabled unless `CORTEX_DEV_WORKBENCH_ENABLED=true`.
- Dev workbench code must not call real Slack, Linear, GitHub, OAuth, model, Kafka,
  Qdrant, MinIO, Redis, or other external services.
- Fixture behavior should be deterministic: stable IDs, idempotent seed/reset,
  traceable pipeline runs, and repeatable retrieval/eval outputs.
- `PipelineEventEnvelope.payload` must not include raw provider payloads, source
  text, chunk text, OCR text, embeddings, vectors, OAuth tokens, or secrets.
- Prefer Pydantic contracts and existing interfaces over ad hoc dictionaries when
  the shape is part of the backend contract.
- Evidence citations should resolve to seeded source objects, files, or chunks.
- Tests should cover disabled/enabled dev route behavior, fixture lifecycle,
  pipeline stage order, retrieval output, evidence packs, context gate results,
  eval metrics, CLI/worker smoke paths, and config redaction.
- Avoid broad abstractions or real production persistence in early phases unless
  the phase plan explicitly calls for it.

If you find an issue, include the concrete file/line, the failure mode, and the
smallest practical fix.
