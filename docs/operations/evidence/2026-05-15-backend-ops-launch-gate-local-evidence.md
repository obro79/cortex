# Backend Ops Launch Gate Local Evidence

Date: 2026-05-15 14:53:26Z
Environment: local
Owner: Codex
Status: not staging evidence

This evidence records no-secret local backend and operations gate checks.
It does not replace staging or live Stripe/provider drill evidence.

## Result

- passed

## Commands

### ruff

`uv run ruff check .`

Result: passed

Output summary:

```
All checks passed!
```

### ruff format

`uv run ruff format --check .`

Result: passed

Output summary:

```
357 files already formatted
```

### mypy

`uv run mypy src`

Result: passed

Output summary:

```
Success: no issues found in 189 source files
```

### focused backend tests

`uv run pytest tests/billing tests/lifecycle tests/permissions tests/deployment tests/smoke/test_worker.py tests/workers/test_provider_acl_worker.py`

Result: passed

Output summary:

```
........................................................................ [ 76%]
......................                                                   [100%]
94 passed in 0.52s
```

### compose config

`docker compose config`

Result: passed

Output summary:

```
name: cortex
services:
  api:
    build:
      context: /Users/owenfisher/Desktop/projects/cortex
      dockerfile: Dockerfile
      target: api
    command:
      - uvicorn
      - cortex.api.app:create_app
      - --factory
      - --host
...
```

### compose lifecycle config

`docker compose --profile lifecycle config`

Result: passed

Output summary:

```
name: cortex
services:
  api:
    build:
      context: /Users/owenfisher/Desktop/projects/cortex
      dockerfile: Dockerfile
      target: api
    command:
      - uvicorn
      - cortex.api.app:create_app
      - --factory
      - --host
...
```

### compose provider-acl config

`docker compose --profile provider-acl config`

Result: passed

Output summary:

```
name: cortex
services:
  api:
    build:
      context: /Users/owenfisher/Desktop/projects/cortex
      dockerfile: Dockerfile
      target: api
    command:
      - uvicorn
      - cortex.api.app:create_app
      - --factory
      - --host
...
```

### alembic heads

`uv run alembic heads`

Result: passed

Output summary:

```
0016_provider_principal_mappings (head)
```

### alembic upgrade sql

`uv run alembic upgrade head --sql`

Result: passed

Output summary:

```
BEGIN;

CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL,
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> 0001_health_checks

CREATE TABLE health_checks (
    id SERIAL NOT NULL,
    name VARCHAR(64) NOT NULL,
...
```

### alembic downgrade sql

`uv run alembic downgrade 0016_provider_principal_mappings:0013_lifecycle_persistence --sql`

Result: passed

Output summary:

```
BEGIN;

-- Running downgrade 0016_provider_principal_mappings -> 0015_provider_acl_snapshots

DROP INDEX ix_provider_principal_mappings_principal;

DROP INDEX ix_provider_principal_mappings_user;

DROP TABLE provider_principal_mappings;

UPDATE alembic_version SET version_num='0015_provider_acl_snapshots' WHERE alembic_version.version_num = '0016_provider_principal_mappings';

...
```

### backup restore static smoke

`uv run python scripts/backup_restore_smoke.py --static`

Result: passed

### derived index static smoke

`uv run python scripts/derived_index_rebuild_smoke.py --static`

Result: passed

### stripe activation static smoke

`uv run python scripts/stripe_activation_smoke.py --static --fake-gateway`

Result: passed

Output summary:

```
{"checkout_session_prefix": "cs", "first_webhook_status": "processed", "portal_session_prefix": "bps", "recorded_webhook_events": 1, "second_webhook_status": "duplicate", "webhook_duplicate": true}
```

## Residual Risk

- Live Stripe checkout, portal, and webhook proof still require Stripe secrets.
- Lifecycle deletion/export still needs a deployed staging drill.
- Provider ACL refresh still needs scheduled staging execution with provider tokens.
- Restore, rollback, load, and cost drills still need staging evidence.

## Follow-Up

- Run this gate before staging drills.
- Append staging drill records in this directory after each live run.
