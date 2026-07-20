# Local MCP API proxy

`cortex-mcp` has an opt-in local proxy for the narrow evidence-only
`get_task_context` tool. It sends the validated task payload to
`POST /v1/context/task-context`; Cortex remains the authorization boundary.

The MCP client cannot set a workspace, actor, session, or authorization field.
Those values are supplied as fixed local process headers, so the API receives
the same authenticated transport identity on every request.

```bash
export CORTEX_MCP_MODE=proxy
export CORTEX_MCP_API_URL=http://127.0.0.1:8000
export CORTEX_MCP_TIMEOUT_SECONDS=10
export CORTEX_MCP_HEADERS_JSON='{"x-cortex-workspace-id":"demo-workspace","x-cortex-auth-email":"demo@example.com"}'
cortex-mcp
```

For the current local public-auth API, `CORTEX_PUBLIC_AUTH_ENABLED=true` is
also required on the API process. `CORTEX_MCP_HEADERS_JSON` may include an
`authorization` header for a future authenticated deployment, but values are
never logged or returned through JSON-RPC. The proxy rejects unsafe transport
headers and invalid configuration, bounds each request to 1–30 seconds, and
reports only redacted diagnostics to stderr. JSON-RPC remains stdout-only.

This is not OAuth, device login, session scraping, or native Claude/Codex
session resume. Fixture mode remains available with `CORTEX_MCP_MODE=fixture`,
and the existing explicit handoff bundle remains session-safe.
