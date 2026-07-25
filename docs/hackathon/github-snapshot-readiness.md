# GitHub snapshot readiness

`uv run python scripts/github_snapshot_smoke.py` is the deterministic GitHub
preflight for this hackathon. It imports a fixed, synthetic pull-request
snapshot into a recording ingestion seam and reports the typed raw event that
would be submitted. The command does not make a network request, read an
environment variable, or display a token.

## Fixture behavior

The `GitHubImportPlan` executes one supplied `GitHubSnapshotPage` at a time.
Each page has a bounded size (1–100) and can carry `next_cursor`; callers can
persist that cursor externally before executing the next supplied page. Every
snapshot item becomes a `RawEventInput` with an idempotency key containing its
repository, object identity, and supplied update version.

The fixture smoke path is deliberately **not live GitHub ingestion**.

## Live prerequisite (not exercised)

Live operation remains on the existing `GitHubConnectorServices.live_backfill`
path. It requires a GitHub App installed on the target repositories, an
installation access token available only to that runtime, and selected
repository/source-connection bindings. The smoke command neither validates nor
prints any of those credentials.
