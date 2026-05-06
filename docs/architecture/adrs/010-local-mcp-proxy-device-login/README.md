# ADR-010: Local MCP Proxy With Device Login

## Status

Accepted.

## Decision

Use a local MCP proxy/CLI that authenticates to hosted Cortex with device login
and exposes tools to Codex and Claude Code.

## What It Is

The local proxy runs on the developer machine as an MCP server. It stores a local
refresh credential/keychain secret after device login, detects repo context, and
forwards tool calls to hosted Cortex.

## Why Cortex Uses It

- Codex and Claude Code work naturally with local MCP/stdio tools.
- Device login avoids copying long-lived API tokens into repo config.
- The proxy can attach local repo path, branch, file hints, and agent identity.
- Hosted Cortex can rotate/revoke sessions centrally.

## Alternatives Considered

- Direct remote API/MCP calls from agents.
- Personal API tokens.
- Repo-scoped static tokens.

## Why Alternatives Lost

- Direct remote calls are less ergonomic for local agent clients.
- Personal tokens are easy to leak.
- Repo-scoped tokens reduce blast radius but increase setup friction.

## Tradeoffs

- Requires installing/running a local helper.
- Device login and token refresh need careful UX.
- Offline behavior is limited unless local cache is added.

## Failure Modes

- Local token leakage.
- Proxy points at wrong workspace/repo.
- Agent blocks on expired credentials without a useful login path.

## How We Test It

- Device login happy path.
- Token refresh/revocation.
- Wrong workspace/repo detection.
- MCP tool smoke tests through the proxy.

## How This Maps From CortexG

`cortexg` has an MCP stdio server. Cortex keeps MCP as the agent interface but
makes it a local proxy to hosted services.

