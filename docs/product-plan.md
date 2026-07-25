# Cortex Product Plan

## One-Line Idea

Cortex is a production context gate and decision-memory layer for AI-heavy engineering teams. It connects to Slack, Linear, GitHub, and repo docs, retrieves task-specific cited context, detects stale or conflicting engineering decisions, and can block Codex or Claude Code until a human approves the canonical path.

## Product Wedge

The first wedge is not generic company search. The wedge is:

> Before an agent implements a Linear issue, Cortex tells it which architecture decisions, diagrams, Slack threads, PRs, and docs constrain the work, and whether any of that context is stale or conflicting.

This is stronger than markdown memory because markdown context is manual, broad, token-heavy, stale-prone, not permission-aware, and not tied to source citations or event freshness.

## Core Pain

AI coding agents are moving fast, but they make wrong implementation choices when they miss prior team decisions. Humans also waste time digging through old docs, Slack threads, diagrams, Linear issues, and PRs to find the context that should have been available at the moment of work.

The expensive failures are:

- Agents follow stale docs instead of newer decisions.
- Agents miss decisions buried in Slack threads.
- Agents implement against the wrong architecture.
- Humans repeatedly sift through scattered sources to find diagrams or rationale.
- Decisions are lost between agent sessions.
- Markdown memory files consume tokens without proving that the right context was loaded.

## Target User

- Primary: engineering teams that use Codex, Claude Code, OpenClaw, Cursor, or other coding agents heavily.
- Buyer/user: technical founder, staff engineer, engineering manager, or platform/devtools owner responsible for agent quality.
- Not first: broad enterprise knowledge management, legal archive, CRM search, or general-purpose internal search.

## Product Thesis

Cortex should become the live decision-context graph for engineering teams using AI agents.

It should:

- ingest where decisions actually happen,
- preserve raw source truth,
- extract decisions, diagrams, constraints, risks, and open questions,
- link context across Slack, Linear, GitHub, and repo docs,
- detect stale or conflicting information,
- serve permission-safe cited context through MCP/API,
- ask a human to approve canonical decisions when ambiguity is risky,
- remember approved resolutions for future agents.

## First Source Set

The first production source set is:

1. Slack
2. Linear
3. GitHub
4. Repo docs

Slack is the wedge connector because high-value architecture decisions and diagrams often happen in threads, files, images, and links, while Slack search is weak for future implementation work.

## Slack Scope

Cortex should ingest broad Slack context but not treat all context as equally important.

Raw capture:

- channel messages,
- threads,
- files,
- images and diagrams,
- links,
- reactions,
- edits and deletes,
- user and channel metadata.

Semantic extraction:

- architecture decisions,
- implementation constraints,
- diagrams and spec references,
- risks,
- open questions,
- owner notes,
- stale assumptions,
- links to Linear, GitHub, and docs.

The product is not "dump Slack history into an agent." The product is "retrieve what matters for this task, cite it, and gate work when the context is unsafe."

## Context Gate

Cortex should be allowed to block an agent when high-impact ambiguity exists.

First gate category:

1. architecture decision conflicts,
2. stale docs versus newer Slack/GitHub/Linear evidence,
3. auth/security/permission-sensitive ambiguity,
4. missing context for a referenced Linear/GitHub task,
5. broad risky changes such as migrations, billing, infra, data deletion, and data access.

Blocking should be narrow and explainable. The agent must receive a clear status:

```text
STATUS: BLOCKED
Reason: Architecture context is conflicted.
Evidence:
  - Slack thread says Postgres sessions were approved.
  - Repo docs still say Redis is the source of truth.
  - GitHub PR partially migrated writes but not reads.
Required action:
  Human must approve, edit, proceed with warning, or stop.
```

## Canonical Decision Model

Cortex can detect ambiguity and draft a resolution, but it cannot silently decide what the team believes.

Trust model:

- Agent proposes.
- Human approves inside Codex or Claude Code.
- Cortex persists the canonical decision with citations, approver, timestamp, and scope.
- Future agents retrieve the canonical decision first.
- Stale source evidence remains visible as background context, not silently hidden.

Conflict behavior:

1. Detect conflicting decisions.
2. Rank evidence by source strength and recency.
3. Return both sides with citations.
4. Draft a recommended canonical decision.
5. Ask the human in the agent workflow.
6. Persist the approved resolution as first-class memory.

## First Wow Demo

The strongest demo starts from the real agent workflow:

> "I'm implementing Linear issue COR-123. What architecture decisions, diagrams, Slack threads, PRs, and docs constrain this implementation, and is any of the context stale or conflicting?"

Example result:

```text
STATUS: BLOCKED

Reason:
Architecture context is conflicted.

Evidence:
1. Slack thread from Apr 18: team agreed to move sessions from Redis to Postgres.
2. Repo docs still say Redis is the source of truth.
3. GitHub PR #184 partially migrated session writes but not reads.
4. Linear COR-119 says rollout was paused pending middleware review.
5. Diagram file from Slack shows intended Postgres session flow.

Proposed canonical decision:
Use Postgres as the future session source of truth, but preserve Redis read fallback until COR-119 is resolved.

Human approval required:
Approve / edit / proceed with warning / stop.
```

The demo proves Cortex can retrieve scattered context, understand source relationships, identify architectural risk, cite evidence, block an agent, and turn a human-approved resolution into durable team memory.

## Product Promise

For any engineering task, Cortex should answer:

- What prior decisions constrain this work?
- Which diagrams, docs, PRs, issues, and threads matter?
- What changed since the last time an agent touched this area?
- Which context is stale, conflicting, missing, or permission-excluded?
- Can the agent proceed, or does a human need to approve the canonical path?

## Production Requirements

Productionization is not a later add-on. It is part of the product definition.
The current architecture choices and tradeoffs are documented in
[`docs/architecture/handbook.md`](architecture/handbook.md).

Required capabilities:

- OAuth connectors for Slack, Linear, and GitHub.
- Repo docs indexing from connected repositories.
- Backfill plus event-driven ingestion.
- Raw event log for replay and audit.
- Derived source objects, chunks, relationships, decisions, and artifacts.
- Scalable indexing for lexical and vector retrieval.
- Permission snapshots and deny-by-default filtering.
- Evidence packs with citations.
- Agent-native approval flow through MCP/CLI.
- Observability for freshness, failures, lag, and excluded context.

## Non-Goals For The First Version

- General-purpose enterprise search.
- Every SaaS connector.
- Fully autonomous canonical decision creation.
- Large admin-heavy SaaS before the agent workflow works.
- Web app as the primary approval surface.
- Blind prompt stuffing of all memory files.

## Product Surface Order

1. MCP tools for Codex/Claude Code context retrieval and gating.
2. CLI for connector setup, source health, local debugging, and approval persistence.
3. Minimal web UI for audit, source health, evidence-pack inspection, and canonical memory history.
4. Slack approval bot after agent-native approvals work.

## Key MCP Tools

- `retrieve_context`: return cited context for a task, issue, repo, and file paths.
- `check_context_gate`: return allow/warn/block based on conflicts, staleness, missing context, and risk category.
- `propose_canonical_decision`: draft a resolution for conflicting evidence.
- `approve_canonical_decision`: persist a human-approved resolution.
- `get_related_work`: find related issues, PRs, threads, docs, diagrams, and prior agent notes.
- `list_sources`: report freshness, permissions, and indexing coverage.

## GStack Workflow

Use gstack as the product and engineering discipline around Cortex:

1. `/office-hours` for idea clarity.
2. `/plan-ceo-review` for scope and product strategy.
3. `/plan-eng-review` before implementing connectors, event ingestion, permissions, or context gates.
4. `/cso` before OAuth/token handling and permission-sensitive retrieval.
5. `/review` before landing production code.
6. `/qa` or `/qa-only` for UI and approval flows.
7. `/context-save` after meaningful planning or architecture sessions.
