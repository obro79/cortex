from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


class SlackRateLimitError(Exception):
    pass


class SlackPermanentError(Exception):
    pass


@dataclass(frozen=True)
class SlackHistoryPage:
    messages: list[dict[str, Any]]
    next_cursor: str | None = None


class SlackWebClient(Protocol):
    async def conversation_history(
        self,
        *,
        channel_id: str,
        cursor: str | None = None,
        oldest: str | None = None,
    ) -> SlackHistoryPage: ...

    async def thread_replies(
        self, *, channel_id: str, thread_ts: str
    ) -> list[dict[str, Any]]: ...


class EmptySlackWebClient:
    async def conversation_history(
        self,
        *,
        channel_id: str,
        cursor: str | None = None,
        oldest: str | None = None,
    ) -> SlackHistoryPage:
        return SlackHistoryPage(messages=[], next_cursor=None)

    async def thread_replies(
        self, *, channel_id: str, thread_ts: str
    ) -> list[dict[str, Any]]:
        return []
