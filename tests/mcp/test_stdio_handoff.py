from cortex.mcp.server import handle_json_rpc_message, list_tool_definitions


def test_tool_discovery_includes_safe_handoff_contract() -> None:
    handoff = next(
        tool
        for tool in list_tool_definitions()
        if tool["name"] == "create_handoff_bundle"
    )

    assert handoff["inputSchema"]["required"] == ["approved_summary"]
    assert "handoff_opt_in" in handoff["inputSchema"]["properties"]


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
    response = await handle_json_rpc_message(
        {"jsonrpc": "2.0", "method": "tools/list"}
    )

    assert response is None
