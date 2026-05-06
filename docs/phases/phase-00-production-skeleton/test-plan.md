# Phase 0 Test Plan

## Commands

```bash
ruff check .
ruff format --check .
mypy src
pytest
docker compose config
```

Optional local smoke:

```bash
docker compose up -d postgres
pytest tests/api tests/contracts
```

## Coverage Map

```txt
Contracts
  ├── status enums exactly match docs
  ├── pipeline envelope accepts valid examples
  ├── pipeline envelope rejects missing required fields
  ├── pipeline envelope rejects forbidden payload keys
  └── entity stubs serialize representative objects

Config
  ├── defaults load without external services
  ├── env overrides apply
  └── sanitized output hides secrets

API
  ├── /health/live returns live
  ├── /health/ready handles optional DB config
  ├── /dev/* unavailable when disabled
  └── /dev/workbench placeholder when enabled

CLI
  ├── cortex --help
  ├── cortex doctor
  └── cortex config hides sensitive values

Worker
  └── cortex-worker --role noop exits cleanly

MCP
  ├── server module imports
  └── planned tool names are registered

Interfaces
  ├── InMemoryEventBus publish/list behavior
  └── placeholder adapters fail clearly

Observability
  ├── logging setup does not require OTEL
  └── redaction removes secret/content-like fields
```

## Tests To Create

| Test file | Assertions |
| --- | --- |
| `tests/contracts/test_entity_status_enums.py` | enum values match `v1-entity-state-schema.md` |
| `tests/contracts/test_pipeline_event_envelope.py` | valid envelope, missing required field errors, forbidden payload keys |
| `tests/api/test_health.py` | liveness/readiness responses |
| `tests/api/test_dev_guard.py` | dev route disabled/enabled behavior |
| `tests/smoke/test_cli.py` | `--help`, `doctor`, sanitized `config` |
| `tests/smoke/test_worker.py` | `noop` role exits cleanly |
| `tests/smoke/test_mcp.py` | MCP module imports and tool names exist |
| `tests/test_config.py` | settings defaults and overrides |
| `tests/test_observability.py` | logging init and redaction |
| `tests/test_event_bus.py` | in-memory event bus behavior |

## Not Required In Phase 0

- real Kafka integration tests,
- Slack/GitHub/Linear connector tests,
- Qdrant vector search tests,
- retrieval quality evals,
- browser tests,
- model provider tests.

Those belong to later phases once real behavior exists.

