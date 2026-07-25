# Phase 9 Test Plan

## Commands

```bash
ruff check .
ruff format --check .
mypy src
pytest
```

Focused local loop:

```bash
pytest tests/connectors/linear tests/connectors/github tests/connectors/repo_docs tests/relationships tests/retrieval tests/context_gate
```

Live API smoke TODO:

```bash
LINEAR_API_TOKEN=... \
GITHUB_INSTALLATION_TOKEN=... \
GITHUB_REPOSITORY=owner/repo \
.venv/bin/python scripts/phase9_live_provider_smoke.py
```

Status: TODO until internal/dev credentials are available. The smoke must print
only counts/status and must not commit provider payloads, issue text, PR text,
private repo names, tokens, or customer data.

## Coverage Map

```txt
Prerequisite
  -> Phase 8.5 unblocked
  -> no customer data before Phase 10 approval

Linear
  -> install/auth
  -> team/project source selection
  -> issue/comment/status/label/assignee backfill
  -> polling/backfill sync
  -> optional webhook/incremental sync if testable
  -> raw event replay
  -> source objects/chunks
  -> allowlist exclusion

GitHub
  -> app/oauth install
  -> repo source selection
  -> issue/PR/review/comment/commit/changed-file backfill
  -> webhook verification/dedupe
  -> raw event replay
  -> source objects/chunks
  -> allowlist exclusion

Repo docs
  -> docs root source selection
  -> markdown/ADR import
  -> content hash no-op
  -> diagram/source-file import
  -> source objects/chunks
  -> allowlist exclusion

Relationships
  -> issue IDs
  -> PR URLs/numbers
  -> commit SHAs
  -> branch names
  -> file paths
  -> Slack permalinks
  -> docs paths
  -> retrieval expansion

Retrieval/gate
  -> COR-123-style cross-source evidence
  -> source coverage
  -> stale/conflicting docs block
  -> missing provider warn/block
```

## Tests To Create

| Test file | Assertions |
| --- | --- |
| `tests/connectors/linear/test_linear_auth.py` | Install/auth success, missing credentials, redaction. |
| `tests/connectors/linear/test_linear_sources.py` | Team/project allowlist selection and exclusion. |
| `tests/connectors/linear/test_linear_backfill.py` | Issues/comments/statuses persist as raw events with idempotency. |
| `tests/connectors/linear/test_linear_sync_scope.py` | Polling/backfill is required; webhook/incremental support is either tested or disabled. |
| `tests/connectors/linear/test_linear_normalization.py` | Raw Linear events replay to source objects/chunks. |
| `tests/connectors/github/test_github_install.py` | App/OAuth install metadata and secret boundary. |
| `tests/connectors/github/test_github_sources.py` | Repo allowlist selection and private repo exclusion. |
| `tests/connectors/github/test_github_backfill.py` | PRs/issues/reviews/comments/commits/changed files persist as raw events. |
| `tests/connectors/github/test_github_webhooks.py` | Webhook verification, dedupe, supported event mapping. |
| `tests/connectors/github/test_github_normalization.py` | Raw GitHub events replay to source objects/chunks. |
| `tests/connectors/test_phase9_live_clients.py` | Mocked Linear/GitHub live API clients send correct auth and map responses to provider-shaped raw events. |
| `tests/connectors/repo_docs/test_docs_importer.py` | Markdown/ADR discovery, content hash no-op, docs source objects/chunks. |
| `tests/connectors/repo_docs/test_docs_raw_event_contract.py` | Imported/changed/deleted docs publish `raw_event.persisted` and replay consistently. |
| `tests/connectors/repo_docs/test_docs_allowlist.py` | Non-allowlisted docs roots do not ingest or leak metadata. |
| `tests/relationships/test_deterministic_parsers.py` | Linear IDs, PR URLs, SHAs, branch names, file paths, Slack permalinks, docs paths. |
| `tests/relationships/test_relationship_builder.py` | Upsert semantics, confidence/method metadata, duplicate no-op. |
| `tests/relationships/test_identity_links_excluded.py` | Provider user IDs do not create cross-provider person identity relationships in Phase 9. |
| `tests/retrieval/test_cross_source_relationship_expansion.py` | Linear issue expands to related Slack/GitHub/docs evidence. |
| `tests/context_gate/test_cross_source_conflicts.py` | Stale docs vs newer Slack/GitHub/Linear evidence returns warn/block. |
| `tests/security/test_phase9_allowlist_redaction.py` | Hidden repo/team/project/docs names, URLs, titles, snippets, IDs do not leak. |

## Golden COR-123 Assertions

Query:

```txt
I'm implementing Linear issue COR-123. What architecture decisions, diagrams,
PRs, and docs constrain this implementation?
```

Expected evidence:

```json
{
  "sources": ["slack", "linear", "github", "repo_docs"],
  "relationships": [
    "slack_thread_to_linear_issue",
    "linear_issue_to_github_pr",
    "slack_thread_to_github_pr",
    "docs_to_code_path"
  ],
  "context_gate_status": "block"
}
```

Expected reason:

```txt
Docs still claim Redis is the session source of truth, while newer Slack,
GitHub, and Linear evidence indicate Postgres is the target with a middleware
fallback blocker.
```

## Redaction Assertions

Search logs, event payloads, API responses, source coverage, evidence packs,
deadletters, and run logs for:

- Linear API keys/tokens,
- GitHub private keys/tokens/webhook secrets,
- private repo names from non-allowlisted repos,
- Linear team/project names from non-allowlisted scopes,
- docs path names from non-allowlisted roots,
- issue/PR/comment/doc text from excluded sources,
- raw provider payload snippets.

Expected result: no hits outside explicit raw payload/object-storage boundaries
and no hidden source identifiers in agent-facing output.

## Data Boundary Assertions

Phase 9 test and manual runs must use:

- deterministic fixtures,
- redacted recorded-real payloads,
- explicit internal/dev provider accounts.

Expected result: no real customer data appears in Phase 9 run logs, fixtures,
screenshots, API responses, or committed artifacts before Phase 10 approval.

## Deferred Live API Assertions

TODO after local internal/dev credentials exist:

- Linear live smoke fetches at least one allowlisted internal/dev issue or exits
  with an explicit no-data status.
- GitHub live smoke fetches at least one allowlisted internal/dev issue, PR, or
  commit from `GITHUB_REPOSITORY` or exits with an explicit no-data status.
- Live smoke output contains only counts/status and workspace/run IDs.
- No tokens, raw provider payloads, private text snippets, or customer data are
  committed.

## Not Required In Phase 9

- Provider-native per-user ACL snapshots,
- AI-first or broad semantic relationship inference,
- full codebase indexing outside docs roots,
- polished connector admin UI,
- production rollout,
- Phase 10 permission/security expansion.
