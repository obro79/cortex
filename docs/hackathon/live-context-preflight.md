# Live Context Proof preflight

This is the credential-free operator gate for the first controlled, real Slack
to Qdrant proof. It does not contact Slack, Qdrant, Gemini, or any provider.
It reports only configuration presence, expected runtime modes, migration-file
availability, and local Docker Compose metadata when Docker is available.

```bash
uv run python scripts/live_context_preflight.py --format json
```

The process exits non-zero while required configuration is absent. That is
expected before secrets are installed. Do not treat a passing preflight as proof
of credential validity, completed migrations, indexed data, or retrieval.

The command reuses the same Slack variable contract as
`scripts/live_sources_preflight.py` and additionally checks the Live Context
runtime contract:

- `CORTEX_EVENT_BUS=kafka`, `CORTEX_STATE_BACKEND=sql`,
  `CORTEX_EMBEDDING_MODE=real`, and `CORTEX_SLACK_CONNECTOR_ENABLED=true`;
- presence of database, Kafka, Qdrant, Gemini, encryption, and Slack settings;
- hosted Qdrant requires HTTPS and `QDRANT_API_KEY` presence;
- a non-empty `QDRANT_COLLECTION_PREFIX`; the concrete collection is runtime
  embedding-profile derived and is deliberately not guessed by preflight.

## Redacted proof report

After the future authenticated live run, save a report matching
[`live-context-run-report.example.json`](live-context-run-report.example.json).
It records only counts, status codes, freshness, the resolved collection name,
and opaque hashes. It must not contain Slack message text, query text,
credentials, source URLs, or raw provider IDs.

```bash
uv run python scripts/live_context_preflight.py \
  --validate-report docs/hackathon/live-context-run-report.example.json
```

The validator is intentionally local and schema-only. The runtime/reporting
owner must create the report from authenticated pipeline and retrieval counters
after the live path exists; this fixture is documentation, not live evidence.
