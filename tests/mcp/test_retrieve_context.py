from cortex.mcp.server import call_tool


async def test_retrieve_context_tool_shape_and_errors() -> None:
    missing = await call_tool("retrieve_context", {"workspace_id": "ws_1"})
    unknown = await call_tool(
        "retrieve_context",
        {"workspace_id": "ws_1", "query": "session", "gate": True},
    )
    response = await call_tool(
        "retrieve_context", {"workspace_id": "ws_1", "query": "session"}
    )

    assert missing == {"ok": False, "error": "missing_required_arguments"}
    assert unknown["error"] == "unknown_arguments"
    assert response["ok"] is True
    assert response["tool"] == "retrieve_context"
    assert "evidence_pack_id" in response
    assert "gate_status" not in response
