# Phase 16 Autoplan Review

## Verdict

Proceed with Slack and GitHub as the first self-serve beta providers. Keep
Linear and repo docs behind the same pattern, but do not block beta setup on
full parity across every source.

## CEO Review

Mode: selective expansion.

The product promise is "connect your work sources and Cortex starts helping."
That promise fails if setup requires a founder in the database. Slack and GitHub
cover enough of the first beta value loop to make self-serve real.

## Design Review

Connector setup should be explicit and trust-building:

- what Cortex will read,
- what the provider asks for,
- what the admin selected,
- what is syncing now,
- what failed and how to fix it.

Avoid hiding provider complexity behind vague success states.

## Engineering Review

Use one setup/action pattern across providers. Provider-specific code belongs in
adapters; workspace scope, permissions, audit, backfill enqueue, and redaction
should be shared.

Primary risks:

- OAuth callbacks not tied to the initiating workspace,
- source selections saved without permission checks,
- tokens appearing in responses or logs,
- backfills started synchronously from web requests,
- connector health built from stale or fake state.

## DX Review

Provider flows need mockable callbacks and deterministic local setup. Tests
should not require live Slack/GitHub accounts for normal CI.

## Decision Log

- Prioritize Slack and GitHub for beta.
- Make Linear and repo docs follow the same connector setup contract.
- Require source selection and backfill progress in the customer UI.
- Require reauth and revoke flows before calling a provider self-serve.

## Approval Conditions

- Setup actions are permissioned, audited, and workspace-scoped.
- OAuth/app-install callbacks bind to the correct workspace.
- Tokens and secrets are never rendered.
- Backfills are asynchronous and observable.
