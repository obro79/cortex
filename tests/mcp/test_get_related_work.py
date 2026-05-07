from cortex.mcp.server import call_tool


async def test_get_related_work_tool_shape() -> None:
    response = await call_tool(
        "get_related_work", {"workspace_id": "ws_1", "query": "COR-123"}
    )

    assert response["ok"] is True
    assert response["tool"] == "get_related_work"
    assert "evidence_pack" in response
    assert "allow" not in response
