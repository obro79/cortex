# Product and Demo Brief

## Product thesis

**Always-current context for every agent.**

Claude, Codex, Cursor, and similar agents can already contact individual
providers. The remaining problem is that each agent must search those providers
at request time, reconcile inconsistent results, and rediscover prior work.
Cortex continuously normalizes approved company context into one
permission-filtered evidence layer so an existing agent starts with current,
cited organizational knowledge.

The product is MCP-first. The UI is a companion control plane for source setup,
freshness, evidence, and graph inspection—not a competing chat product.

## Hero story

`COR-123` migrates sessions from Redis to Postgres. A partial rollout preserves
a stale Redis read fallback, causing users to be logged out after deployment.

Developer A investigates in Claude Code. An explicitly installed Cortex hook
publishes a structured, redacted checkpoint containing the task, decisions,
safe file summaries, test outcome, and next action. Developer A leaves.

A new synthetic Slack message confirms that affected pods still have the Redis
fallback enabled. Cortex ingests and indexes it. Developer B opens Claude Code
and asks:

> Pick up the COR-123 session incident. Use Cortex before changing anything.
> Tell me what Developer A established, what changed since then, the likely
> cause, conflicting evidence, and the safest next file and test to inspect.

Claude calls Cortex through MCP. The response combines the prior checkpoint with
the newer Slack message, GitHub rollout PR, Jira incident, support email, and
stale Drive document. Claude states the likely cause, cites the evidence, names
the next file and test, and waits for approval before editing.

## Audience and judging outcome

The primary audience is a technical hackathon judge who understands developer
agents but may not understand retrieval architecture.

Within three minutes, the judge should understand:

1. Cortex is a context layer used by existing agents.
2. It prepares company knowledge before a prompt instead of searching six
   providers sequentially.
3. It preserves source, permissions, freshness, conflicts, and citations.
4. Agent work can become an approved checkpoint without a manual handoff doc.
5. A later Slack message changes what the next developer receives.

## Source roles

| Provider | Mode | Decisive record |
| --- | --- | --- |
| GitHub | Imported snapshot | PR #184 keeps the Redis read fallback during the Postgres rollout. |
| Drive/docs | Imported snapshot | An older rollout doc incorrectly treats Redis as the current source of truth. |
| Email | Imported snapshot | Support escalation establishes logout impact and timing. |
| Jira | Imported snapshot | SES-42 records severity, deploy version, and incident owner. |
| Claude Code | Imported structured checkpoint | Developer A identifies the fallback path and next test. |
| Slack | Live synthetic message | The newest update confirms the affected pods still use the fallback. |

Twelve additional records provide realistic noise: unrelated session work,
older resolved incidents, superseded comments, rollout coordination, and
lexically similar but irrelevant authentication material.

## Three-minute performance

| Time | Beat | Proof |
| --- | --- | --- |
| 0:00–0:20 | Play the source-convergence intro video. | Sources and Developer A's checkpoint become Cortex context. |
| 0:20–0:35 | State the problem and thesis. | “Always-current context for every agent.” |
| 0:35–0:45 | Activate six source cards. | Pre-indexed snapshot catalog with honest mode labels. |
| 0:45–1:05 | Post the prepared Slack update. | Actual synthetic Slack message in the demo channel. |
| 1:05–1:20 | Return to the evidence graph. | New live Slack node fades into COR-123. |
| 1:20–2:15 | Ask Developer B's Claude Code question. | MCP returns current cited context. |
| 2:15–2:35 | Open Slack, checkpoint, and stale-doc nodes. | Freshness, prior work, and conflict are inspectable. |
| 2:35–2:50 | Show architecture/proof slide. | One pipeline, Postgres canonical, Qdrant derived. |
| 2:50–3:00 | Close. | One context layer, every agent, no manual handoff. |

## Success criteria

- The live Slack node appears within ten seconds of webhook receipt.
- The second evidence pack includes all six decisive source types within eight
  evidence items.
- New Slack evidence ranks ahead of stale contradictory documentation.
- The response exposes freshness, source coverage, conflict state, trace ID,
  and inspectable citations.
- Claude names the runnable middleware file and focused pytest but does not edit.
- No secret, raw transcript, private source body, or native session handle
  appears in logs, browser responses, screenshots, slides, or video.
- Two consecutive rehearsals complete in under three minutes.

## Non-goals

- Live OAuth for GitHub, Jira, email, or Drive.
- Native Claude session resume, fork, inspection, or control.
- General chat, a global company graph, SSO, billing, or production connector
  administration.
- Live media extraction.
- Claiming production readiness or customer-scale retrieval quality.

## Recovery behavior

- If Slack delivery fails, use the signed webhook simulator and display a
  fallback label.
- If hosted Qdrant is unavailable, use the Compose run captured against the same
  collection contract and label it local.
- If Claude output drifts, show the recorded MCP exchange tied to the verified
  evidence-pack ID.
- Public artifacts must never silently replace a failed live step with a
  simulation.
