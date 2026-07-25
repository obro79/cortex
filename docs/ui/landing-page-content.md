# Landing Page Content

The landing page should follow the Linear Intake rhythm closely: numbered
chapters, short product claims, figure-labeled visuals, and dense product
screenshots. Cortex should not copy Linear's wording, assets, or exact layout.

## 1.0 Cortex

- Section headline: `Give every agent the context it needs to build correctly.`
- Section intent: introduce Cortex as the shared context layer for MCP, CLI,
  and UI access.
- Supporting copy intent: Cortex connects Slack, GitHub, Linear, and repo docs
  so agents can retrieve current, permission-aware context before changing code.
- Primary CTA: `Log in`.
- Secondary CTA: `See setup`.
- Figure `FIG. 1.1`: a product-system map.
  - Left: engineer prompt, Codex, Claude, CLI, and MCP.
  - Center: Cortex as the context router.
  - Right: Slack, GitHub, Linear, and repo docs.
  - Bottom: cited context bundle with evidence, freshness, and permission
    signals.

## 1.1 Ask

- Section headline: `Ask for the context behind the work.`
- Section intent: show the user or agent asking a concrete engineering question.
- Supporting copy intent: an engineer should not hunt through tools manually
  before building. The agent can ask Cortex for the relevant product decisions,
  source discussions, issues, PRs, and docs.
- Figure `FIG. 1.2`: prompt-to-agent panel.
  - A user asks: `What should I know before changing billing plan enforcement?`
  - The agent decides to call Cortex.
  - Mode chips show `MCP`, `CLI`, and `UI`.

## 1.2 Retrieve

- Section headline: `Pull live context from the systems teams already use.`
- Section intent: show Cortex retrieving from connected sources.
- Supporting copy intent: Cortex searches normalized source objects and chunks
  across selected providers while respecting workspace scope and permissions.
- Figure `FIG. 1.3`: retrieval in progress.
  - Provider columns for Slack, GitHub, Linear, and repo docs.
  - Each column shows a real-looking object type: Slack thread, PR, issue,
    architecture doc.
  - A small status rail shows freshness, selected source count, and excluded
    results.

## 1.3 Verify

- Section headline: `Every answer comes with source truth.`
- Section intent: make evidence and provenance the trust hook.
- Supporting copy intent: Cortex returns cited context, source coverage,
  freshness signals, and permission decisions so an agent can continue with
  confidence.
- Figure `FIG. 1.4`: evidence pack inspector.
  - Top: original query.
  - Middle: cited evidence cards.
  - Right rail: freshness, permission exclusions, source coverage.
  - Bottom: links to source object and agent trace.

## 1.4 Build

- Section headline: `Let the agent continue with the right constraints.`
- Section intent: close the loop from context retrieval to implementation.
- Supporting copy intent: the context bundle can be copied, passed through MCP,
  fetched from the CLI, or inspected in the UI before the agent writes code.
- Figure `FIG. 1.5`: context bundle handed back to an agent.
  - Left: Cortex response with citations.
  - Center: agent working plan.
  - Right: changed code or PR preparation panel.
  - Labels show `fresh`, `cited`, `workspace-scoped`, and `permission-aware`.

## Final CTA

- Headline: `Make company context available where work happens.`
- Primary CTA: `Log in`.
- Secondary CTA: `Read developer setup`.
- Content intent: point both product users and technical users to the right
  entry point without adding a broad marketing site.
