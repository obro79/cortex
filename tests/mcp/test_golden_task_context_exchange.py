from __future__ import annotations

import json
from pathlib import Path

from cortex.mcp.server import create_local_proxy_server
from cortex.retrieval.task_context import TaskContextRequest

FIXTURE = (
    Path(__file__).parents[2]
    / "fixtures"
    / "golden_incident"
    / "mcp_get_task_context.json"
)


class _UnusedProxy:
    async def get_task_context(self, request: TaskContextRequest) -> dict[str, object]:
        raise AssertionError(f"not called: {request}")


def test_golden_exchange_freezes_single_simple_mcp_tool() -> None:
    exchange = json.loads(FIXTURE.read_text())
    request = TaskContextRequest.model_validate(exchange["request"])
    server = create_local_proxy_server(task_context_proxy=_UnusedProxy())

    assert exchange["tool"] == "get_task_context"
    assert {tool["name"] for tool in server.tool_definitions()} == {
        "get_task_context"
    }
    assert request.task.issue_ids == ["COR-123"]
    assert request.budget.maximum_evidence_items == 6
    assert request.budget.maximum_tokens == 2000
    assert exchange["pre_live_assertions"]["forbidden_fixture_id"] == (
        "slack-live-fallback-confirmation"
    )
    assert exchange["post_live_assertions"]["next_action_must_change"] is True
