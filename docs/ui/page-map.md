# Cortex UI Page Map

The UI should prove that Cortex makes current company context available through
MCP, CLI, and UI surfaces. Dashboards and administration support the product,
but they should not lead the first experience.

## Landing

- Path: `/`
- Purpose: explain Cortex before login.
- Primary content: one-line product thesis, MCP/CLI/UI access paths, connected
  sources, evidence-backed output, and trust/freshness language.
- Primary CTA: `Log in` and `Request access`.
- Source data dependency: none for v1; use designed product visuals and
  carefully labeled example content.

## Login

- Path: `/login`
- Purpose: get a user into a workspace-scoped Cortex session.
- Primary content: email or auth-provider login, workspace access explanation,
  and short permission-aware context note.
- Primary CTA: `Continue to workspace`.
- Source data dependency: auth session, user, workspace membership, and active
  workspace context. The first implementation can use the current internal
  session path while the page presents the intended product shape.

## Context Console

- Path: `/ui/context`
- Purpose: let a user ask Cortex for the context an agent needs.
- Primary content: context query input, source filters, access mode selector
  for `MCP`, `CLI`, and `UI`, cited context bundle, freshness summary, and
  permission exclusion summary.
- Primary CTA: `Get context`.
- Secondary CTAs: `Copy for agent`, `Open evidence`, `Open source`.
- Source data dependency: retrieval service, source chunks, evidence packs,
  provider filters, freshness metadata, and permission decision summaries.

## Agent Trace

- Path: `/ui/traces/:trace_id`
- Purpose: show what Cortex gave an agent, CLI, MCP client, or UI request.
- Primary content: request origin, original query, retrieved providers, selected
  evidence, excluded evidence, freshness warnings, and resulting context bundle.
- Primary CTA: `Open evidence pack`.
- Source data dependency: trace metadata, retrieval request records, evidence
  pack records, permission decisions, and source object references.

## Evidence Viewer

- Path: `/ui/evidence/:evidence_pack_id`
- Purpose: make each answer inspectable.
- Primary content: original question, cited chunks, source coverage, freshness
  status, conflict or stale-context signals, permission decisions, and linked
  source objects.
- Primary CTA: `Open source object`.
- Source data dependency: evidence pack repository, retrieval request
  repository, source chunk repository, source object repository, and provider
  ACL decision data where available.

## Source Browser

- Paths: `/ui/sources`, `/ui/sources/:source_id`,
  `/ui/sources/:source_id/objects/:object_id`
- Purpose: pull up anything Cortex knows from a connected source.
- Primary content: provider selector, source list, object list, object detail,
  chunks, files, metadata, relationships, and evidence links.
- Primary CTA: `Open object`.
- Source data dependency: connector source repositories, source object
  repository, source file repository, source chunk repository, and payload
  references. Raw payload display should stay off by default.

## Source Health

- Path: `/ui/health`
- Purpose: show whether context is fresh enough to trust.
- Primary content: connected sources, selected scopes, sync status, freshness,
  cursor position, last backfill, latest error, reauth warnings, and stale ACL
  warnings.
- Primary CTA: `Review source`.
- Source data dependency: source connection repositories, OAuth installation
  repositories, cursor repositories, backfill job repositories, provider ACL
  freshness reports, and scheduler/worker status.

## Connectors

- Path: `/ui/connectors`
- Purpose: connect the systems agents need context from.
- Primary content: Slack, GitHub, Linear, and repo-docs connection cards,
  authorization status, selected scopes, backfill status, and reauthorization
  warnings.
- Primary CTA: `Connect source`.
- Secondary CTAs: `Select sources`, `Reauthorize`, `Run backfill`.
- Source data dependency: connector setup services, OAuth installation
  repositories, source selection repositories, billing/plan enforcement, and
  permission checks.

## Developer Setup

- Path: `/ui/setup` or `/docs`
- Purpose: show how to use Cortex from MCP, CLI, and UI.
- Primary content: MCP setup snippet, CLI examples, UI context-console link, and
  example agent prompt.
- Primary CTA: `Copy MCP config`.
- Source data dependency: workspace config, API keys or token references where
  supported, and safe redacted setup metadata.

## Later Settings And Admin

- Paths: `/ui/settings`, `/ui/team`, `/ui/billing`,
  `/ui/lifecycle`, `/ui/provider-acls`
- Purpose: support customer administration after the core context flow works.
- Primary content: members, roles, billing portal, retention policy,
  deletion/export requests, provider principal mappings, and workspace settings.
- Primary CTA: page-specific admin action.
- Source data dependency: tenancy repositories, billing repositories, lifecycle
  repositories, provider principal mapping repositories, and audit logs.

## Later Optional Pages

- Canonical decisions and conflicts.
- Support diagnostics.
- Cost and usage.
- Visual relationship graph.
- Saved context bundles for repeated agent tasks.
