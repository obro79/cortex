from __future__ import annotations

import json

import httpx

from cortex.mcp.proxy import ApiTaskContextProxy, LocalMcpProxyConfig
from cortex.mcp.server import create_local_proxy_server, handle_json_rpc_message


def _config() -> LocalMcpProxyConfig:
    return LocalMcpProxyConfig.from_environment(
        {
            "CORTEX_MCP_API_URL": "http://cortex.local",
            "CORTEX_MCP_HEADERS_JSON": json.dumps(
                {
                    "x-cortex-workspace-id": "configured-workspace",
                    "x-cortex-auth-email": "configured@example.com",
                    "authorization": "Bearer configured-token",
                }
            ),
        }
    )


async def test_local_proxy_uses_only_configured_transport_identity() -> None:
    observed: dict[str, object] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        observed["url"] = str(request.url)
        observed["headers"] = dict(request.headers)
        observed["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "ok": False,
                "status": "failed",
                "trace_id": "api-trace",
                "live_data": True,
                "error": {
                    "code": "RETRIEVAL_UNAVAILABLE",
                    "message": "temporary",
                    "retryable": True,
                },
            },
        )

    server = create_local_proxy_server(
        task_context_proxy=ApiTaskContextProxy(
            _config(), transport=httpx.MockTransport(handler)
        )
    )

    response = await server.call_tool(
        "get_task_context",
        {"task": {"objective": "find rollout context"}},
    )

    assert response["trace_id"] == "api-trace"
    assert observed["url"] == "http://cortex.local/v1/context/task-context"
    headers = observed["headers"]
    assert isinstance(headers, dict)
    assert headers["x-cortex-workspace-id"] == "configured-workspace"
    assert headers["x-cortex-auth-email"] == "configured@example.com"
    assert headers["authorization"] == "Bearer configured-token"
    assert observed["body"] == {
        "task": {
            "objective": "find rollout context",
            "repository": None,
            "branch": None,
            "issue_ids": [],
            "pull_request_numbers": [],
            "file_hints": [],
        },
        "filters": {"providers": [], "source_ids": []},
        "freshness": {"maximum_age_seconds": 3600, "require_fresh": False},
        "budget": {"maximum_evidence_items": 12, "maximum_tokens": 4000},
    }


async def test_tool_arguments_cannot_override_configured_transport_identity() -> None:
    calls = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(500)

    server = create_local_proxy_server(
        task_context_proxy=ApiTaskContextProxy(
            _config(), transport=httpx.MockTransport(handler)
        )
    )

    response = await server.call_tool(
        "get_task_context",
        {
            "workspace_id": "attacker-workspace",
            "actor_id": "attacker",
            "task": {"objective": "find rollout context"},
        },
    )

    assert calls == 0
    assert response["ok"] is False
    assert response["error"]["code"] == "INVALID_ARGUMENTS"


async def test_local_proxy_redacts_upstream_errors() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, text="Bearer secret-token was rejected")

    proxy = ApiTaskContextProxy(_config(), transport=httpx.MockTransport(handler))
    server = create_local_proxy_server(task_context_proxy=proxy)

    response = await server.call_tool(
        "get_task_context", {"task": {"objective": "find rollout context"}}
    )

    assert response == {
        "ok": False,
        "status": "failed",
        "error": {
            "code": "MCP_PROXY_REJECTED",
            "message": "Configured Cortex API rejected the request.",
            "retryable": False,
        },
    }


def test_local_proxy_config_rejects_unsafe_headers() -> None:
    try:
        LocalMcpProxyConfig.from_environment(
            {
                "CORTEX_MCP_API_URL": "http://cortex.local",
                "CORTEX_MCP_HEADERS_JSON": '{"host":"attacker.local"}',
            }
        )
    except ValueError as error:
        assert "not allowed" in str(error)
    else:
        raise AssertionError("unsafe configured header must be rejected")


async def test_proxy_mode_discovery_is_limited_to_proxy_and_safe_handoff() -> None:
    server = create_local_proxy_server(
        task_context_proxy=ApiTaskContextProxy(
            _config(),
            transport=httpx.MockTransport(lambda request: httpx.Response(500)),
        )
    )

    response = await handle_json_rpc_message(
        {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}, server=server
    )

    assert response is not None
    tools = response["result"]["tools"]
    assert {tool["name"] for tool in tools} == {
        "get_task_context",
        "create_handoff_bundle",
    }
