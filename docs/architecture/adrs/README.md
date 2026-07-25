# Cortex ADRs

Each top-level ADR is a topic directory. The root `README.md` in each directory
is the accepted decision record for that topic. Deeper planning can be added
inside the same directory without flattening the architecture docs.

Recommended structure:

```txt
adrs/
  005-hybrid-retrieval-stack/
    README.md
    implementation-plan.md
    eval-plan.md
    child-adrs/
      001-query-planning.md
      002-ranking-formula.md
```

Use nested ADRs when a topic has multiple meaningful sub-decisions. Keep the
top-level `README.md` as the durable summary that links to the deeper records.

Current top-level ADRs:

- [ADR-001: Python FastAPI Backend](001-python-fastapi-backend/)
- [ADR-002: Kafka Event Backbone](002-kafka-event-backbone/)
- [ADR-003: Hosted-First Data Boundary](003-hosted-first-data-boundary/)
- [ADR-004: Postgres Source Of Truth](004-postgres-source-of-truth/)
- [ADR-005: Hybrid Retrieval Stack](005-hybrid-retrieval-stack/)
- [ADR-006: Provider-Neutral Embeddings](006-provider-neutral-embeddings/)
- [ADR-007: Source-Aware Chunking](007-source-aware-chunking/)
- [ADR-008: Deterministic-First Linking](008-deterministic-first-linking/)
- [ADR-009: Source Allowlist Permissions V1](009-source-allowlist-permissions-v1/)
- [ADR-010: Local MCP Proxy With Device Login](010-local-mcp-proxy-device-login/)
- [ADR-011: Slack Files And Diagrams Via Metadata And OCR](011-slack-files-diagrams-ocr/)
- [ADR-012: Secrets And Token Management](012-secrets-token-management/)
- [ADR-013: Webhook Security And Idempotency](013-webhook-security-idempotency/)
- [ADR-014: Retention And Deletion](014-retention-deletion/)
- [ADR-015: Rate Limits Backpressure And Repair](015-rate-limits-backpressure-repair/)
- [ADR-016: Retrieval Evals And Model Gateway](016-retrieval-evals-model-gateway/)
- [ADR-017: Dev Workbench And Deterministic Pipeline Fixtures](017-dev-workbench-deterministic-fixtures/)
- [ADR-018: Grafana Cloud Lean Observability](018-grafana-cloud-lean-observability/)
- [ADR-019: Containerized Services Kubernetes Compatible](019-containerized-services-kubernetes-compatible/)
- [ADR-020: Layered Platform Components](020-layered-platform-components/)
- [ADR-021: Distributed Coordination Without Custom Leader](021-distributed-coordination-without-custom-leader/)
- [ADR-022: Apache Kafka Runtime](022-apache-kafka-runtime/)
