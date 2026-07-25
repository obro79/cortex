# ADR-009: Source Allowlist Permissions V1

## Status

Accepted.

## Decision

Use source allowlists as the v1 permissions model. Admins explicitly choose which
Slack channels, GitHub repos, Linear teams/projects, and docs roots Cortex may
index and retrieve.

## What It Is

Source allowlists define the approved data scopes for a workspace. Cortex does
not ingest, index, retrieve, or expose non-allowlisted source content.

## Why Cortex Uses It

- Full provider-native per-user ACL sync is complex.
- V1 still needs a privacy boundary stronger than "index everything."
- Source allowlists are understandable to early users and cheap to implement.

## Alternatives Considered

- Full provider-native per-user ACL snapshots in v1.
- Workspace trust: all workspace users can retrieve all connected data.
- Warn-only permissions.

## Why Alternatives Lost

- Full ACL parity is too much before connector behavior is proven.
- Workspace trust is too broad for Slack/private repos.
- Warn-only permissions are unsafe for source data.

## Tradeoffs

- Users inside an allowlisted workspace may still see all allowlisted source
  context in v1.
- Private channel/repo semantics are approximated by admin selection.
- Later ACL work must refine, not replace, the source-scope model.

## Failure Modes

- Accidentally indexing an unapproved channel/repo is a serious bug.
- Debug/source coverage output could leak non-allowlisted names.
- Allowlist changes require clear deletion/reindex behavior.

## How We Test It

- Non-allowlisted sources never create retrievable chunks.
- Retrieval/debug output does not expose non-allowlisted names, URLs, file names,
  or snippets.
- Allowlist removal triggers deindex/delete behavior.

## How This Maps From CortexG

`cortexg` models permission grants and deny behavior. Cortex v1 chooses a simpler
source-scope model first, then can add provider-native per-user snapshots later.

