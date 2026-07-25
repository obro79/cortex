from __future__ import annotations

import base64
from urllib.parse import parse_qs

import httpx

from cortex.connectors.slack.client import RealSlackWebClient, SlackHttpClient
from cortex.connectors.slack.oauth import RealSlackOAuthClient


async def test_real_oauth_client_exchanges_code_with_basic_auth() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/oauth.v2.access"
        encoded_auth = base64.b64encode(b"client-id:client-secret").decode()
        assert request.headers["authorization"] == f"Basic {encoded_auth}"
        form = parse_qs(request.content.decode())
        assert form["code"] == ["oauth-code"]
        assert form["redirect_uri"] == ["http://localhost/callback"]
        return httpx.Response(
            200,
            json={
                "ok": True,
                "access_token": "xoxb-live-token",
                "scope": "channels:read,channels:history,groups:read",
                "team": {"id": "T123"},
                "bot_user_id": "B123",
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        oauth = RealSlackOAuthClient(
            client_id="client-id",
            client_secret="client-secret",
            redirect_uri="http://localhost/callback",
            http=SlackHttpClient(client=client),
        )

        token = await oauth.exchange_code("oauth-code")

    assert token.access_token == "xoxb-live-token"
    assert token.team_id == "T123"
    assert token.bot_user_id == "B123"
    assert "channels:history" in token.scopes


async def test_real_web_client_uses_bearer_token_and_pagination() -> None:
    seen: list[tuple[str, dict[str, str]]] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer xoxb-live-token"
        seen.append((request.url.path, dict(request.url.params)))
        if request.url.path == "/api/conversations.history":
            return httpx.Response(
                200,
                json={
                    "ok": True,
                    "messages": [{"ts": "1.000", "text": "hello"}],
                    "response_metadata": {"next_cursor": "next-page"},
                },
            )
        return httpx.Response(
            200,
            json={"ok": True, "messages": [{"ts": "1.001", "text": "reply"}]},
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        slack = RealSlackWebClient(SlackHttpClient(client=client))
        history = await slack.conversation_history(
            access_token="xoxb-live-token",
            channel_id="C123",
            cursor="cursor-1",
            oldest="0.900",
        )
        replies = await slack.thread_replies(
            access_token="xoxb-live-token",
            channel_id="C123",
            thread_ts="1.000",
        )

    assert history.next_cursor == "next-page"
    assert history.messages == [{"ts": "1.000", "text": "hello"}]
    assert replies == [{"ts": "1.001", "text": "reply"}]
    assert seen[0][0] == "/api/conversations.history"
    assert seen[0][1]["channel"] == "C123"
    assert seen[0][1]["cursor"] == "cursor-1"
    assert seen[0][1]["oldest"] == "0.900"
    assert seen[1][0] == "/api/conversations.replies"
    assert seen[1][1]["ts"] == "1.000"
