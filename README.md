# Cortex

Production-shaped backend skeleton for Cortex. Phase 0 creates the app spine,
contracts, entrypoints, local infrastructure, and smoke tests without building
real ingestion, retrieval, connectors, auth, or admin UI.

## Quickstart

```bash
python -m pip install -e ".[dev]"
ruff check .
ruff format --check .
mypy src
pytest
docker compose config
```

Run the API locally:

```bash
uvicorn cortex.api.app:create_app --factory --reload
```

Run shell entrypoints:

```bash
cortex doctor
cortex config
cortex-worker --role noop
```

## Environment

Copy `.env.example` for local overrides. Tests pass with no external services.
Infrastructure URLs are optional in local mode and clients are initialized
lazily.

## Phase 0 Non-goals

- No real Slack, Linear, GitHub, or repo-doc connectors.
- No Kafka consumers or publication beyond interfaces/placeholders.
- No retrieval, indexing, ranking, context gate, or canonical memory behavior.
- No production auth, admin UI, Kubernetes, Temporal, or required Redis.
