from cortex.mcp.server import McpServer
from cortex.runtime import CortexAuthority, create_local_runtime


async def test_injected_mcp_authority_ignores_client_workspace_claim() -> None:
    server = McpServer(
        runtime=create_local_runtime(),
        authority=CortexAuthority(
            workspace_id="ws_1", actor_id="user_1", trace_id="trace_1"
        ),
    )

    denied = await server.call_tool(
        "retrieve_context", {"workspace_id": "other", "query": "session"}
    )
    allowed = await server.call_tool("retrieve_context", {"query": "session"})

    assert denied["error"] == "workspace_scope_mismatch"
    assert allowed["ok"] is True
