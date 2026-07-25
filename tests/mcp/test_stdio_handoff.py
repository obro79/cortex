from cortex.mcp.server import McpServer, handle_json_rpc_message, list_tool_definitions
from cortex.runtime import CortexAuthority, create_local_runtime


def test_tool_discovery_includes_safe_handoff_contract() -> None:
    handoff = next(
        tool
        for tool in list_tool_definitions()
        if tool["name"] == "create_handoff_bundle"
    )

    assert handoff["inputSchema"]["required"] == ["approved_summary"]
    assert "handoff_opt_in" in handoff["inputSchema"]["properties"]


def test_canonical_tool_schemas_exclude_host_derived_authority_fields() -> None:
    definitions = {tool["name"]: tool for tool in list_tool_definitions()}

    proposal = definitions["propose_canonical_decision"]["inputSchema"]
    approval = definitions["approve_canonical_decision"]["inputSchema"]

    assert proposal["additionalProperties"] is False
    assert "workspace_id" not in proposal["properties"]
    assert "actor_id" not in proposal["properties"]
    assert approval["additionalProperties"] is False
    assert "actor_id" not in approval["properties"]


async def test_json_rpc_tools_call_returns_handoff_without_session_access() -> None:
    response = await handle_json_rpc_message(
        {
            "jsonrpc": "2.0",
            "id": 7,
            "method": "tools/call",
            "params": {
                "name": "create_handoff_bundle",
                "arguments": {
                    "approved_summary": "Proceed with the approved rollout.",
                    "evidence_references": ["ep_123"],
                },
            },
        }
    )

    assert response is not None
    result = response["result"]
    assert result["isError"] is False
    assert result["structuredContent"]["bundle"]["session_accessed"] is False


async def test_json_rpc_requires_an_injected_server_for_authorized_tools() -> None:
    request = {
        "jsonrpc": "2.0",
        "id": "retrieval",
        "method": "tools/call",
        "params": {
            "name": "retrieve_context",
            "arguments": {"workspace_id": "other", "query": "session"},
        },
    }

    unbound = await handle_json_rpc_message(request)
    server = McpServer(
        runtime=create_local_runtime(),
        authority=CortexAuthority(
            workspace_id="ws_1", actor_id="human_1", trace_id="trace_1"
        ),
    )
    bound = await handle_json_rpc_message(request, server=server)

    assert unbound is not None
    assert unbound["result"]["structuredContent"] == {
        "ok": False,
        "error": "authority_unavailable",
    }
    assert bound is not None
    assert bound["result"]["structuredContent"]["error"] == "unknown_arguments"


async def test_json_rpc_fixture_mode_uses_the_standard_tool_schema() -> None:
    response = await handle_json_rpc_message(
        {
            "jsonrpc": "2.0",
            "id": "fixture",
            "method": "tools/call",
            "params": {
                "name": "retrieve_context",
                "arguments": {"query": "session"},
            },
        },
        fixture_mode=True,
    )

    assert response is not None
    assert response["result"]["structuredContent"]["ok"] is True


async def test_json_rpc_rejects_invalid_parameters() -> None:
    response = await handle_json_rpc_message(
        {
            "jsonrpc": "2.0",
            "id": "bad-params",
            "method": "tools/call",
            "params": {"name": "create_handoff_bundle", "arguments": []},
        }
    )

    assert response is not None
    assert response["error"] == {"code": -32602, "message": "Invalid params"}


async def test_json_rpc_rejects_invalid_request_shapes_and_ids() -> None:
    invalid_id = await handle_json_rpc_message(
        {"jsonrpc": "2.0", "id": True, "method": "tools/list"}
    )
    missing_method = await handle_json_rpc_message({"jsonrpc": "2.0", "id": 4})
    blank_tool_name = await handle_json_rpc_message(
        {
            "jsonrpc": "2.0",
            "id": "blank-tool",
            "method": "tools/call",
            "params": {"name": " ", "arguments": {}},
        }
    )

    assert invalid_id == {
        "jsonrpc": "2.0",
        "id": None,
        "error": {"code": -32600, "message": "Invalid Request"},
    }
    assert missing_method == {
        "jsonrpc": "2.0",
        "id": 4,
        "error": {"code": -32600, "message": "Invalid Request"},
    }
    assert blank_tool_name == {
        "jsonrpc": "2.0",
        "id": "blank-tool",
        "error": {"code": -32602, "message": "Invalid params"},
    }


async def test_json_rpc_preserves_notifications_without_emitting_responses() -> None:
    response = await handle_json_rpc_message({"jsonrpc": "2.0", "method": "tools/list"})

    assert response is None
