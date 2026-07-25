# Phase 16 Implementation Checklist

## Prerequisites

- [ ] Phase 15 tenant/auth/onboarding is complete.
- [ ] Workspace admin role can be resolved for UI and API actions.
- [ ] Connector repositories/services expose install and source state.
- [ ] Backfill job queue/status paths exist.

## Shared Connector Setup

- [ ] Add connector setup overview page.
- [x] Add provider setup service interface.
- [x] Add source selection service interface.
- [x] Add connector health read model.
- [x] Add data-read explanation content per provider.
- [x] Add permission checks for setup, source selection, reauth, revoke, and
      backfill retry.
- [x] Audit allowed and denied setup actions.
- [x] Redact tokens, secrets, private URLs, and raw payloads.

## Slack

- [ ] Add Slack install entrypoint.
- [ ] Add Slack OAuth/app install callback handling.
- [ ] Show Slack workspace/team status.
- [ ] List selectable channels or source scopes.
- [ ] Save selected source scopes.
- [ ] Enqueue initial backfill.
- [ ] Add reauth and revoke flows.

## GitHub

- [ ] Add GitHub App install entrypoint.
- [ ] Add install callback handling.
- [ ] Show organization/account install status.
- [ ] List selectable repositories.
- [ ] Save selected repo scopes.
- [ ] Enqueue initial backfill.
- [ ] Add reauth and revoke flows.

## Linear And Docs

- [ ] Add Linear setup flow if provider service exists.
- [ ] Add Linear team/project source selection.
- [ ] Add repo docs import setup.
- [ ] Show import status and retry.

## Closeout

- [ ] Add setup flow tests for each implemented provider.
- [x] Add denied-action tests for non-admin users.
- [ ] Add workspace isolation tests.
- [x] Add token/secret redaction tests.
- [ ] Add browser smoke for Slack and GitHub setup.
