# Cortex Frontend

This is the Next.js frontend for Cortex product UI work.

The first UI direction is not a dashboard. It starts with an agent-context flow:

1. A visitor understands Cortex as MCP, CLI, and UI access to live company
   context.
2. A user logs into a workspace.
3. A user asks Cortex what an agent needs to know.
4. Cortex returns cited, permission-aware context with links to evidence and
   source truth.

## Commands

```bash
npm install
npm run dev
npm run typecheck
npm run lint
npm run build
```

## Initial Routes

- `/`: Linear-inspired product landing page.
- `/login`: workspace access entry.
- `/ui/context`: authenticated task-context diagnostic.
- `/ui/evidence/[evidencePackId]`: authenticated evidence-pack record inspector.
- `/ui/health`: local API readiness display.
- `/ui/mcp`: MCP capability/setup status (no unverified launch command).
- `/ui/pipeline/[runId]`: local-fixture pipeline run reference.

The same-origin BFF only proxies allowlisted API paths. Its documented fixture
read routes are `GET /api/cortex/dev/state`,
`GET /api/cortex/dev/pipeline/runs/[runId]`, and
`GET /api/cortex/dev/evidence-packs/[evidencePackId]`; they remain available
only when the backend's local dev workbench is enabled. It does not expose
fixture mutation or execution routes to the browser.
