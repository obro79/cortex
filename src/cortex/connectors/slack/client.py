from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

import httpx

SlackQueryParams = dict[str, str | int | bool]


class SlackRateLimitError(Exception):
    pass


class SlackPermanentError(Exception):
    pass


class SlackOAuthError(Exception):
    pass


@dataclass(frozen=True)
class SlackHistoryPage:
    messages: list[dict[str, Any]]
    next_cursor: str | None = None


class SlackWebClient(Protocol):
    async def conversations_list(
        self,
        *,
        access_token: str,
        cursor: str | None = None,
        types: str = "public_channel,private_channel",
    ) -> SlackHistoryPage: ...

    async def conversation_history(
        self,
        *,
        access_token: str,
        channel_id: str,
        cursor: str | None = None,
        oldest: str | None = None,
    ) -> SlackHistoryPage: ...

    async def thread_replies(
        self, *, access_token: str, channel_id: str, thread_ts: str
    ) -> list[dict[str, Any]]: ...


class EmptySlackWebClient:
    async def conversations_list(
        self,
        *,
        access_token: str,
        cursor: str | None = None,
        types: str = "public_channel,private_channel",
    ) -> SlackHistoryPage:
        return SlackHistoryPage(messages=[], next_cursor=None)

    async def conversation_history(
        self,
        *,
        access_token: str,
        channel_id: str,
        cursor: str | None = None,
        oldest: str | None = None,
    ) -> SlackHistoryPage:
        return SlackHistoryPage(messages=[], next_cursor=None)

    async def thread_replies(
        self, *, access_token: str, channel_id: str, thread_ts: str
    ) -> list[dict[str, Any]]:
        return []


class SlackHttpClient:
    def __init__(
        self,
        *,
        base_url: str = "https://slack.com/api",
        timeout: float = 10.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.client = client

    async def api_get(
        self,
        method: str,
        *,
        access_token: str,
        params: SlackQueryParams,
    ) -> dict[str, Any]:
        headers = {"Authorization": f"Bearer {access_token}"}
        if self.client is not None:
            response = await self.client.get(
                f"{self.base_url}/{method}",
                params=params,
                headers=headers,
            )
        else:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/{method}",
                    params=params,
                    headers=headers,
                )
        return self._parse_response(response)

    async def oauth_access(
        self,
        *,
        client_id: str,
        client_secret: str,
        code: str,
        redirect_uri: str | None,
    ) -> dict[str, Any]:
        data: dict[str, str] = {"code": code}
        if redirect_uri:
            data["redirect_uri"] = redirect_uri
        if self.client is not None:
            response = await self.client.post(
                f"{self.base_url}/oauth.v2.access",
                data=data,
                auth=(client_id, client_secret),
            )
        else:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/oauth.v2.access",
                    data=data,
                    auth=(client_id, client_secret),
                )
        return self._parse_response(response, oauth=True)

    def _parse_response(
        self, response: httpx.Response, *, oauth: bool = False
    ) -> dict[str, Any]:
        if response.status_code == 429:
            raise SlackRateLimitError("slack_rate_limited")
        if response.status_code >= 500:
            raise SlackRateLimitError("slack_transient_error")
        if response.status_code >= 400:
            raise SlackPermanentError("slack_http_error")
        payload = response.json()
        if not isinstance(payload, dict):
            raise SlackPermanentError("slack_invalid_response")
        if payload.get("ok") is not True:
            error = str(payload.get("error", "slack_api_error"))
            if error == "ratelimited":
                raise SlackRateLimitError(error)
            if oauth:
                raise SlackOAuthError(error)
            raise SlackPermanentError(error)
        return payload


class RealSlackWebClient:
    def __init__(self, http: SlackHttpClient | None = None) -> None:
        self.http = http or SlackHttpClient()

    async def conversations_list(
        self,
        *,
        access_token: str,
        cursor: str | None = None,
        types: str = "public_channel,private_channel",
    ) -> SlackHistoryPage:
        params: SlackQueryParams = {"limit": 100, "types": types}
        if cursor:
            params["cursor"] = cursor
        payload = await self.http.api_get(
            "conversations.list", access_token=access_token, params=params
        )
        metadata = payload.get("response_metadata")
        next_cursor = (
            str(metadata.get("next_cursor") or "") if isinstance(metadata, dict) else ""
        )
        channels = payload.get("channels", [])
        if not isinstance(channels, list):
            raise SlackPermanentError("slack_invalid_channels")
        return SlackHistoryPage(
            messages=[
                dict(channel) for channel in channels if isinstance(channel, dict)
            ],
            next_cursor=next_cursor or None,
        )

    async def conversation_history(
        self,
        *,
        access_token: str,
        channel_id: str,
        cursor: str | None = None,
        oldest: str | None = None,
    ) -> SlackHistoryPage:
        params: SlackQueryParams = {"channel": channel_id, "limit": 100}
        if cursor:
            params["cursor"] = cursor
        if oldest:
            params["oldest"] = oldest
            params["inclusive"] = False
        payload = await self.http.api_get(
            "conversations.history", access_token=access_token, params=params
        )
        metadata = payload.get("response_metadata")
        next_cursor = (
            str(metadata.get("next_cursor") or "") if isinstance(metadata, dict) else ""
        )
        messages = payload.get("messages", [])
        if not isinstance(messages, list):
            raise SlackPermanentError("slack_invalid_messages")
        return SlackHistoryPage(
            messages=[
                dict(message) for message in messages if isinstance(message, dict)
            ],
            next_cursor=next_cursor or None,
        )

    async def thread_replies(
        self, *, access_token: str, channel_id: str, thread_ts: str
    ) -> list[dict[str, Any]]:
        payload = await self.http.api_get(
            "conversations.replies",
            access_token=access_token,
            params={"channel": channel_id, "ts": thread_ts, "limit": 100},
        )
        messages = payload.get("messages", [])
        if not isinstance(messages, list):
            raise SlackPermanentError("slack_invalid_replies")
        return [dict(message) for message in messages if isinstance(message, dict)]
