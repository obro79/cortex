# Phase 16 Plan: Self-Serve Connector Setup

## Goal

Let a customer admin connect sources without developer help, starting with Slack
and GitHub as the beta path.

Success means an admin can install/connect sources, choose what Cortex reads,
watch backfill progress, reauthorize or revoke access, and see connector health
inside their workspace.

## Inputs

- [`../phase-15-self-serve-product/plan.md`](../phase-15-self-serve-product/plan.md)
- [`../phase-08-real-slack-connector/plan.md`](../phase-08-real-slack-connector/plan.md)
- [`../phase-09-linear-github-repo-docs/plan.md`](../phase-09-linear-github-repo-docs/plan.md)
- [`../phase-10-permissions-security/plan.md`](../phase-10-permissions-security/plan.md)
- [`../phase-14-minimal-web-ui/plan.md`](../phase-14-minimal-web-ui/plan.md)

## Non-Goals

- Do not add billing enforcement.
- Do not solve provider-native per-user retrieval ACLs unless Phase 10 already
  exposes them.
- Do not build every provider to the same depth before Slack and GitHub work.
- Do not expose raw provider payloads in setup or health pages.

## Product Flow

1. Admin opens connector setup in an active workspace.
2. Admin chooses provider.
3. Cortex shows scopes and data-read explanation.
4. Admin completes OAuth/app install/API-key import as provider requires.
5. Admin selects channels/repos/teams/docs roots.
6. Cortex starts backfill and shows progress.
7. Connector health reports fresh, stale, failed, revoked, or needs attention.

## Architecture

```text
Workspace admin UI
  -> connector setup service
  -> provider install adapter
  -> source selection service
  -> audit + permissions
  -> backfill job enqueue
  -> connector health read model
```

Provider adapters should normalize install status, available sources, selected
sources, reauth state, revoke behavior, and backfill trigger behavior.

## Provider Scope

Beta priority:

- Slack app install and channel/source selection.
- GitHub App install and repo selection.

Second priority:

- Linear API or OAuth setup.
- Repo docs import flow.

## Exit Criteria

- A workspace admin can connect Slack and GitHub without manual database edits.
- Backfill progress and failures are visible.
- Reauth and revoke paths are audited and safe.
- Non-admin users are denied connector setup actions without data leakage.
