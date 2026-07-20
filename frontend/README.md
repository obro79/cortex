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
- `/ui/context`: authenticated context-console placeholder.
