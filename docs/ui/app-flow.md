# Cortex App Flow

The first app flow should center on context retrieval for agents, not dashboard
metrics. Source health, connectors, and activity pages support trust after the
user sees Cortex answer a real context question.

## Flow 1: Visitor To Context

1. Visitor opens the landing page.
2. Visitor sees Cortex as MCP, CLI, and UI access to live company context.
3. Visitor chooses `Log in`.
4. Visitor authenticates and resolves an active workspace.
5. Visitor lands on `/ui/context`, not a dashboard.
6. Visitor asks what an agent needs to know.
7. Cortex returns a cited context bundle.
8. Visitor opens evidence or source detail from the result.

## Flow 2: Agent-Ready Context

1. User enters a task-oriented query in `/ui/context`.
2. User optionally chooses source filters.
3. Cortex retrieves relevant chunks and source objects.
4. Cortex displays a compact answer/context bundle.
5. Cortex shows citations, freshness, and permission exclusions.
6. User copies the context for an agent or opens the agent trace.
7. Agent proceeds with the context and constraints.

## Flow 3: Evidence Inspection

1. User opens an evidence link from a context result.
2. Evidence viewer shows the original query and selected citations.
3. User sees which providers contributed context.
4. User sees stale, conflict, or permission signals.
5. User opens the source object behind a citation.
6. Source detail shows metadata, chunks, files, and related evidence.

## Flow 4: Source Trust Check

1. User notices stale or missing evidence in a context result.
2. User opens source health.
3. Source health shows last sync, cursor, backfill, and latest error.
4. User opens connector detail or source browser.
5. User can reauthorize, run backfill, or select sources where permissions
   allow.

## Flow 5: Developer Setup

1. User opens setup from landing page or authenticated UI.
2. User chooses MCP, CLI, or UI path.
3. Setup page shows the relevant connection instructions.
4. User copies the safe config or command.
5. User can test a sample context request.

## Navigation Priority

Initial authenticated navigation should be:

1. Context
2. Sources
3. Evidence
4. Health
5. Connectors
6. Setup

Activity, team, billing, lifecycle, and provider ACL administration can follow
after the context path works.

## Empty States

- No sources connected: show connector setup and a sample context query.
- No search results: show source filters and health links.
- No evidence pack: explain that evidence appears after a context request.
- No trace: show MCP, CLI, and UI setup options.
- Stale source: show health status and the relevant connector action.
