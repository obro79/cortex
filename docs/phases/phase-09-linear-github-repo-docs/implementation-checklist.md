# Phase 9 Implementation Checklist

## 0. Phase 8.5 Gate

- Confirm final Phase 8.5 report says `UNBLOCKED_FOR_PHASE_9`.
- Confirm no P0/P1 Phase 8.5 findings remain open.
- Carry forward accepted residual risks into Phase 9 notes.
- Confirm Phase 9 data sources are fixtures, redacted recorded-real data, or
  explicit internal/dev accounts only.

Acceptance:

- Phase 9 work does not start from a blocked Slack connector foundation,
- Phase 9 does not ingest real customer data before Phase 10 approval.

Commit:

- no code commit; record prerequisite confirmation in first Phase 9 PR/commit
  notes.

## 1. Shared Connector Foundations

- Reuse Phase 8 connector persistence and secret/source/cursor/job abstractions.
- Add any provider-neutral fields needed for Linear/GitHub/docs without
  hardcoding provider-only concepts into shared records.
- Add source allowlist records for Linear teams/projects, GitHub repos, and docs
  roots.

Acceptance:

- provider-neutral mapper tests pass,
- source allowlist tests cover all three new source types.

Commit:

- `phase 9: extend connector foundations`

## 2. Linear Connector

- Implement Linear install/auth path.
- Implement team/project source selection.
- Implement issue/comment/project/status/label/assignee backfill.
- Implement polling/backfill as the required v1 sync path.
- Treat webhook/incremental sync as an optional sub-slice only if Linear support
  is clear and testable.
- Persist Linear raw events.
- Normalize to Linear source objects/chunks.
- Expose Linear source health.

Acceptance:

- allowlisted Linear issues/comments ingest and replay,
- unallowlisted teams/projects do not leak,
- Linear source coverage appears in evidence packs.

Commit:

- `phase 9: add Linear connector`

## 3. GitHub Connector

- Implement GitHub App/OAuth install path.
- Implement repo source selection.
- Implement issue/PR/review/comment/commit/changed-file backfill.
- Implement webhook delivery verification/dedupe where available.
- Persist GitHub raw events.
- Normalize to GitHub source objects/chunks.
- Expose GitHub source health.

Acceptance:

- allowlisted repo issues/PRs/comments/commits ingest and replay,
- private/non-allowlisted repos do not leak,
- GitHub source coverage appears in evidence packs.

Commit:

- `phase 9: add GitHub connector`

## 4. Repo Docs Importer

- Implement docs root source selection.
- Discover markdown/ADR/architecture docs under allowlisted roots.
- Hash docs and skip unchanged content.
- Import diagrams/images through existing source-file/OCR path where supported.
- Persist docs import events.
- Publish `raw_event.persisted` for imported/changed/deleted docs.
- Normalize docs to source objects/chunks.
- Expose docs import freshness/health.

Acceptance:

- allowlisted docs roots import and replay,
- non-allowlisted paths do not leak,
- stale docs can be detected against newer Slack/GitHub/Linear evidence.

Commit:

- `phase 9: add repo docs importer`

## 5. Deterministic Relationship Builder

- Add parsers for Linear issue IDs.
- Add parsers for GitHub PR/issue URLs and numbers.
- Add parsers for commit SHAs.
- Add parsers for branch names and file paths.
- Add parsers for Slack permalinks and docs paths.
- Upsert relationship records with method, confidence, evidence ref, and status.
- Publish pointer-only relationship events.
- Exclude cross-provider person identity links; Phase 10 owns identity mapping.

Acceptance:

- Linear issue to GitHub PR links work,
- Slack thread to Linear issue links work,
- Slack thread to GitHub PR links work,
- docs to code path links work,
- diagrams/files to source components link where deterministic evidence exists.

Commit:

- `phase 9: add deterministic relationships`

## 6. Retrieval And Context Gate Integration

- Extend retrieval relationship expansion across new relationship types.
- Add source coverage for Linear/GitHub/docs.
- Ensure context gate sees missing/stale/conflicting provider evidence.
- Preserve permission exclusions without leaking hidden source metadata.

Acceptance:

- COR-123-style query returns Slack, Linear, GitHub, and docs citations,
- stale docs versus newer Slack/GitHub/Linear evidence can block,
- missing referenced Linear/GitHub task context can warn/block.

Commit:

- `phase 9: integrate cross-source retrieval`

## 7. Health, Repair, And Replay

- Add health summaries for Linear, GitHub, docs importer, and relationships.
- Add retry/deadletter visibility for provider failures.
- Add replay tests for each provider/importer.
- Document repair flow for stale cursors/import jobs.

Acceptance:

- provider failures are visible without crashing retrieval,
- replay rebuilds source objects/relationships from raw/import events.

Commit:

- `phase 9: add provider health and replay`

## 8. Tests And Docs

- Add tests listed in [`test-plan.md`](test-plan.md).
- Update setup docs with redacted provider configuration examples.
- Add run-log template for Phase 9 connector smoke tests.
- TODO: document the local internal/dev credential setup for live Linear and
  GitHub API smoke runs.
- TODO: run and record the live API smoke with `LINEAR_API_TOKEN` and/or
  `GITHUB_INSTALLATION_TOKEN`/`GITHUB_TOKEN` plus `GITHUB_REPOSITORY` once those
  credentials are available.

Acceptance:

- `ruff check .` passes.
- `ruff format --check .` passes.
- `mypy src` passes.
- focused Phase 9 tests pass.
- existing Slack/retrieval/gate tests still pass.

Commit:

- `phase 9: complete connector docs and tests`

## Commit Cadence

Do not build Phase 9 as one large provider mega-commit. Use separate commits for
Linear, GitHub, repo docs, relationships, retrieval integration, and health.

Recommended order:

1. Shared connector foundation updates.
2. Linear connector.
3. GitHub connector.
4. Repo docs importer.
5. Deterministic relationship builder.
6. Cross-source retrieval/context-gate integration.
7. Health/replay/repair.
8. Final docs/tests cleanup.

Each commit should include focused tests for that slice. Keep provider commits
independent enough that a GitHub bug does not block reviewing Linear ingestion.

## Deferred Live API Setup TODO

The current implementation includes outbound Linear/GitHub clients, mocked HTTP
tests, and `scripts/phase9_live_provider_smoke.py`. Real provider API validation
is intentionally deferred until an internal/dev Linear API token and GitHub
installation token are available in the local environment. Do not use real
customer data for this TODO; Phase 10 owns customer-data approval.
