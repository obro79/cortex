from cortex.mcp.server import McpServer, list_tool_definitions
from cortex.runtime import CortexAuthority, create_local_runtime


async def test_get_task_context_uses_host_authority_and_rejects_tenancy_fields() -> (
    None
):
    server = McpServer(
        runtime=create_local_runtime(),
        authority=CortexAuthority(
            workspace_id="ws_1", actor_id="actor_1", trace_id="trace_1"
        ),
    )

    denied = await server.call_tool(
        "get_task_context",
        {"workspace_id": "other", "task": {"objective": "session migration"}},
    )
    result = await server.call_tool(
        "get_task_context", {"task": {"objective": "session migration"}}
    )

    assert denied["error"]["code"] == "INVALID_ARGUMENTS"
    assert result["ok"] is True
    assert result["trace_id"] == "trace_1"
    assert "answer" not in result


def test_get_task_context_is_registered_with_a_strict_schema() -> None:
    tool = next(
        item for item in list_tool_definitions() if item["name"] == "get_task_context"
    )

    assert tool["inputSchema"]["additionalProperties"] is False
    assert "workspace_id" not in tool["inputSchema"]["properties"]
    assert tool["description"].startswith(
        "Pull bounded, permission-filtered company context"
    )
