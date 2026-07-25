# Cortex UI Planning

This folder is the durable home for Cortex UI direction. It describes the
product story, page map, landing-page content, app flow, and visual reference
before implementation work starts.

Cortex gives agents, CLIs, MCP clients, and humans fresh company context from
Slack, GitHub, Linear, and repo docs. The UI should make that context easy to
request, inspect, verify, and trace back to source truth.

## Documents

- [Page Map](page-map.md): all planned pages, primary content, CTAs, and data
  dependencies.
- [Landing Page Content](landing-page-content.md): Linear Intake-inspired
  chapter structure, section intent, and figure descriptions.
- [App Flow](app-flow.md): the end-to-end journey from public page to
  evidence-backed context.
- [Visual Reference](visual-reference.md): the Linear-style product-page
  language Cortex should follow without copying assets or wording.
- [Component And Content Plan](component-content-plan.md): per-page component,
  state, data, and acceptance plan for implementation.
- [Image Asset Prompts](image-asset-prompts.md): GPT image prompt inventory and
  guidance for which visuals should stay CSS-built product UI.

## Local Control Plane (implemented slice)

The local Next control plane begins at `/ui/context` and is deliberately a
fixture-only surface. It carries the persistent `SYNTHETIC FIXTURES · NOT LIVE`
disclosure, has no login/SSO simulation or general chat, and allows only these
local FastAPI operations through its same-origin BFF:

- `GET /health/live`, `GET /health/ready`, and optional `GET /dev/state`
- fixture seed/reset, pipeline run/status, focused retrieval, and an evidence
  pack by known ID

The BFF rejects all other paths and methods. `/ui/evidence/:id`,
`/ui/pipeline/:id`, `/ui/health`, and `/ui/mcp` are scoped companion routes;
they do not claim live connector data or arbitrary source exploration.

## Product Principle

The first authenticated UI surface is the context console, not a dashboard. A
user should arrive, ask what an agent needs to know, receive cited context, and
open the evidence or source behind it.
