# Phase 9 Plan: Linear, GitHub, Repo Docs, And Relationships

## Goal

Add the remaining v1 engineering sources after Slack has passed the Phase 8.5
review gate:

```txt
Linear connector
GitHub connector
Repo docs importer
  -> raw_events / source_objects / source_files
  -> chunks + indexes
  -> deterministic relationships
  -> retrieval/evidence packs
  -> context gate
```

Phase 9 makes task-aware context work end to end. A query like "I'm
implementing Linear issue COR-123" should retrieve the Linear issue, related
GitHub PRs/commits, linked Slack decisions, relevant docs, stale/conflicting
evidence, and source coverage.

## Prerequisite Gate

Phase 9 must not start until Phase 8.5 has a final report with
`UNBLOCKED_FOR_PHASE_9`.

If Phase 8.5 is `BLOCKED`, implement the blocking Phase 8 fixes first, then add
Phase 8.5 recheck evidence before starting Phase 9 work.

## Data Boundary

Phase 9 may use deterministic fixtures, local dev data, redacted recorded-real
payloads, and explicitly approved internal/dev provider accounts. It must not
ingest real customer data or be treated as customer-ready until Phase 10 passes
`APPROVED_FOR_REAL_CUSTOMER_DATA`.

## Inputs

- [`../implementation-roadmap.md`](../implementation-roadmap.md#phase-9-linear--github--repo-docs)
- [`../phase-08-5-slack-review-manual-testing/plan.md`](../phase-08-5-slack-review-manual-testing/plan.md)
- [`../../architecture/handbook.md`](../../architecture/handbook.md)
- [`../../architecture/v1-entity-state-schema.md`](../../architecture/v1-entity-state-schema.md)
- [`../../architecture/pipeline-event-envelope.md`](../../architecture/pipeline-event-envelope.md)
- [`../../architecture/adrs/008-deterministic-first-linking/README.md`](../../architecture/adrs/008-deterministic-first-linking/README.md)
- [`../../architecture/adrs/009-source-allowlist-permissions-v1/README.md`](../../architecture/adrs/009-source-allowlist-permissions-v1/README.md)
- [`../phase-02-raw-event-pipeline/plan.md`](../phase-02-raw-event-pipeline/plan.md)
- [`../phase-03-normalization-source-objects/plan.md`](../phase-03-normalization-source-objects/plan.md)
- [`../phase-04-chunking-indexing/plan.md`](../phase-04-chunking-indexing/plan.md)
- [`../phase-05-retrieval-evidence-packs/plan.md`](../phase-05-retrieval-evidence-packs/plan.md)
- [`../phase-06-context-gate/plan.md`](../phase-06-context-gate/plan.md)

## Existing Foundation

Earlier phases provide:

- production-shaped connector patterns from Slack,
- OAuth/secret/source-connection/cursor/webhook/backfill records,
- raw-event persistence and replay,
- fixture normalizers for Linear, GitHub, and repo docs,
- source-aware chunking for Linear issues, GitHub PRs, and docs,
- hybrid retrieval, evidence packs, context gate, and canonical memory,
- source allowlist concepts for provider/source boundaries.

Phase 9 should reuse these patterns instead of building provider-specific
retrieval paths.

## Non-Goals

- No provider-native per-user ACL snapshots; source allowlists remain v1.
- No full Phase 10 security/permissions expansion.
- No AI-first relationship inference; deterministic links first.
- No broad semantic code understanding beyond markdown/docs import and changed
  file/path relationships.
- No full GitHub code search/indexing of every source file unless it is under
  an allowlisted docs root.
- No polished connector admin UI beyond minimal source selection and health.
- No production rollout beyond Phase 9 validation.
- No real customer data ingestion before Phase 10 approval.
- No cross-provider person identity mapping; Phase 10 owns later-ready identity
  mapping.

## Architecture

```txt
LinearConnector
  -> OAuth/API key install
  -> team/project source selection
  -> issue/comment backfill
  -> webhook/incremental sync where available
  -> raw_event.persisted

GitHubConnector
  -> GitHub App/OAuth install
  -> repo source selection
  -> issue/PR/review/comment/commit backfill
  -> webhook delivery
  -> raw_event.persisted

RepoDocsImporter
  -> docs root source selection
  -> markdown/diagram discovery
  -> docs import job
  -> raw_event.persisted

RelationshipBuilder
  -> parse identifiers/URLs/paths
  -> upsert deterministic relationships
  -> publish relationship.upserted
  -> retrieval relationship expansion
```

Provider connectors own API calls, source selection, cursors, webhooks, retries,
and health. The shared pipeline owns raw payload storage, normalization,
chunking, indexing, retrieval, gates, and canonical decisions.

## Proposed Module Layout

```txt
src/cortex/connectors/
  linear/
    oauth.py
    client.py
    sources.py
    backfill.py
    webhooks.py
    mapping.py
    health.py
  github/
    app.py
    client.py
    sources.py
    backfill.py
    webhooks.py
    mapping.py
    health.py
  repo_docs/
    importer.py
    discovery.py
    mapping.py
    health.py

src/cortex/relationships/
  deterministic.py
  parsers.py
  repository.py
  service.py
  publishers.py

tests/connectors/linear/
tests/connectors/github/
tests/connectors/repo_docs/
tests/relationships/
```

Keep provider-specific mapping near each connector. Keep relationship parsing
provider-aware but storage provider-neutral.

## Linear Scope

Ingest:

- issues,
- comments,
- project/team metadata,
- labels,
- statuses,
- assignees,
- blockers/relations when available.

Source allowlist:

- Linear teams and/or projects.

Raw event rules:

- one raw event per provider-shaped issue/comment/update unit,
- idempotency by workspace/team/project/issue/comment/update ID,
- source object key: `linear:{workspace_id}:{issue_id}`.

Normalization target:

- `SourceObject(object_type=linear_issue)`,
- chunks for issue overview, comments, updates, and blocker notes.

## GitHub Scope

Ingest:

- repos,
- issues,
- pull requests,
- PR reviews,
- PR comments,
- issue comments,
- commits,
- changed files.

Source allowlist:

- selected GitHub repositories.

Raw event rules:

- one raw event per issue/PR/review/comment/commit/change unit where practical,
- idempotency by installation/repo/event object IDs,
- source object keys:
  - `github:{installation_id}:{repo_id}:pr:{number}`,
  - `github:{installation_id}:{repo_id}:issue:{number}`,
  - `github:{installation_id}:{repo_id}:commit:{sha}`.

Normalization target:

- `SourceObject(object_type=github_pull_request)`,
- `SourceObject(object_type=github_issue)`,
- `SourceObject(object_type=github_commit)`,
- chunks for PR overview, reviews/comments, changed files, commits.

## Repo Docs Scope

Ingest:

- markdown docs,
- ADRs,
- architecture docs,
- diagrams/images referenced by docs where metadata/OCR path supports them.

Source allowlist:

- explicit repo/docs roots, not whole private repo contents by default.

Import rules:

- record docs import jobs and cursors by repo/ref/path root,
- hash file content and skip unchanged docs,
- represent each imported/changed/deleted doc as a raw-event-like record and
  publish `raw_event.persisted` so replay and audit stay consistent,
- source object key: `doc:{repo_id}:{path}`.

Normalization target:

- `SourceObject(object_type=repo_doc)`,
- `SourceFile` for referenced diagrams/images when fetched,
- chunks for markdown sections and OCR text where available.

## Relationship Builder

Build deterministic links first:

- Linear issue IDs in Slack, GitHub, docs, branch names, and PR titles,
- GitHub PR numbers and URLs in Slack, Linear, docs, and commits,
- commit SHAs in PRs/docs/Slack,
- file paths in docs, PR changed files, Slack messages, and Linear issues,
- Slack permalinks in Linear/GitHub/docs,
- docs paths referenced from issues/PRs/Slack.

Do not create cross-provider person identity links in Phase 9. Provider user ID
mapping is Phase 10 work and should stay out of deterministic relationship
expansion until the identity model and redaction rules exist.

Relationship records should include:

- from/to object or chunk IDs,
- relationship type,
- deterministic method,
- confidence,
- evidence reference,
- parser/version metadata,
- status.

Do not create AI candidate links in Phase 9 unless all deterministic links are
working and tests already pass. If AI candidates are added, they must be
`candidate` status with citations and lower retrieval authority.

## Retrieval And Gate Integration

Phase 9 must prove:

- task hints can anchor retrieval on a Linear issue,
- relationship expansion reaches related GitHub PRs/commits/docs/Slack threads,
- source coverage reports missing or stale providers safely,
- context gate blocks when Slack/GitHub/Linear/docs disagree,
- non-allowlisted repo/team/project/docs roots do not leak names, URLs, titles,
  snippets, chunk IDs, or debug IDs.

## Events

Publish existing pointer-only events:

- `raw_event.persisted` for Linear/GitHub/docs import inputs,
- existing source object/chunk/index events from downstream phases,
- `relationship.upserted` for deterministic links.

Event payloads must not include issue text, PR body, comments, docs snippets,
private repo names, file names from non-allowlisted sources, tokens, installation
secrets, or raw payload snippets.

## Health And Coverage

Expose provider/source health for:

- install/auth status,
- allowlisted sources,
- last backfill/import time,
- cursor freshness,
- webhook delivery health where applicable,
- retry/deadletter counts,
- docs import freshness,
- relationship build counts,
- source coverage used by evidence packs.

## Acceptance Criteria

Phase 9 is complete when:

- Phase 8.5 has approved Phase 9 start.
- Linear issues/comments/projects/statuses from allowlisted scopes ingest and
  normalize.
- GitHub issues/PRs/reviews/comments/commits/changed files from allowlisted
  repos ingest and normalize.
- Repo docs roots import markdown/ADRs/docs and diagrams through existing
  source-object/source-file paths.
- Deterministic relationships link Linear, GitHub, Slack, docs, commits, and
  file paths.
- Retrieval for the COR-123-style task returns Slack, Linear, GitHub, and docs
  evidence with citations and source coverage.
- Context gate can block on stale/conflicting Slack/GitHub/Linear/docs evidence.
- Source allowlists prevent ingestion/retrieval/debug leakage from
  non-allowlisted sources.
