# Provider ACL Refresh Runbook

This runbook covers scheduled provider-native ACL snapshot refresh for Slack,
GitHub, and Linear.

## Required Configuration

Run the worker with:

- `CORTEX_STATE_BACKEND=sql`
- `DATABASE_URL`
- `CORTEX_PROVIDER_ACL_REFRESH_TARGETS_JSON`
- `CORTEX_PROVIDER_ACL_PRINCIPAL_MAPPINGS_JSON` when provider principals need
  explicit user mapping
- `CORTEX_PROVIDER_ACL_REFRESH_LEASE_TTL_SECONDS`
- `CORTEX_PROVIDER_ACL_SNAPSHOT_TTL_HOURS`

Refresh target entries must include a `token_env` field. Do not put provider
tokens directly in JSON. The worker reads the token from the named runtime
environment variable and never records it in refresh results.

## Target Shape

Slack channel:

```json
{
  "workspace_id": "ws_...",
  "provider": "slack",
  "resource_type": "slack_channel",
  "channel_id": "C...",
  "source_connection_id": "srcconn_...",
  "token_env": "SLACK_BOT_TOKEN"
}
```

GitHub repository:

```json
{
  "workspace_id": "ws_...",
  "provider": "github",
  "resource_type": "github_repository",
  "repository_id": "123456",
  "owner": "acme",
  "repo": "app",
  "source_connection_id": "srcconn_...",
  "token_env": "GITHUB_INSTALLATION_TOKEN"
}
```

Linear team:

```json
{
  "workspace_id": "ws_...",
  "provider": "linear",
  "resource_type": "linear_team",
  "team_id": "team_...",
  "source_connection_id": "srcconn_...",
  "token_env": "LINEAR_API_TOKEN"
}
```

Principal mapping:

```json
{
  "workspace_id": "ws_...",
  "user_id": "usr_...",
  "provider": "slack",
  "principal_type": "user",
  "external_id": "U...",
  "match_method": "admin_configured"
}
```

## Execution

Local/config preflight:

```bash
docker compose --profile provider-acl config
uv run pytest tests/permissions tests/smoke/test_worker.py tests/workers/test_provider_acl_worker.py
```

Scheduled worker execution:

```bash
cortex-worker --role provider-acl
```

The worker uses the scheduler lease `provider-acl-refresh` so only one refresh
run executes at a time.

## Evidence To Record

Record only:

- deploy revision,
- environment,
- worker instance ID,
- resource counts by provider and resource type,
- freshness status counts,
- failure error codes,
- alert count,
- operator and timestamp.

Do not record:

- provider tokens,
- raw Slack channel IDs,
- GitHub repository names when a hash or count is sufficient,
- Linear team names,
- user emails,
- raw provider payloads.
