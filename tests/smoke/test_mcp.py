from cortex.mcp.server import call_tool, list_tools


async def test_mcp_tool_names_are_registered() -> None:
    tools = list_tools()
    assert "retrieve_context" in tools
    assert "approve_canonical_decision" in tools

    result = await call_tool("retrieve_context", {"query": "x"})
    assert result["error"] == "missing_required_arguments"
