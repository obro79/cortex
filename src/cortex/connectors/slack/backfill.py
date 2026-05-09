from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from cortex.contracts.entities import BackfillJob
from cortex.ingestion.raw_events import RawEventIdempotencyConflict, RawEventInput
from cortex.ingestion.service import IngestionResult
from cortex.platform.rate_limits import (
    RateLimitExceededError,
    RateLimitPolicy,
    RateLimitService,
    RateLimitSubject,
)
from cortex.utils.asyncio import maybe_await

from .client import SlackPermanentError, SlackRateLimitError, SlackWebClient
from .mapping import derived_raw_events_for_message


@dataclass(frozen=True)
class SlackBackfillResult:
    ok: bool
    job: BackfillJob
    raw_events_created: int
    duplicates: int
    cursor_value: str | None


class SlackBackfillIngestionService(Protocol):
    async def ingest(self, item: RawEventInput) -> IngestionResult: ...


class SlackBackfillService:
    def __init__(
        self,
        *,
        client: SlackWebClient,
        source_connections: Any,
        installations: Any,
        secrets: Any,
        cursors: Any,
        backfills: Any,
        ingestion: SlackBackfillIngestionService,
        provider_rate_limiter: RateLimitService | None = None,
        provider_rate_limit_policy: RateLimitPolicy | None = None,
    ) -> None:
        self.client = client
        self.source_connections = source_connections
        self.installations = installations
        self.secrets = secrets
        self.cursors = cursors
        self.backfills = backfills
        self.ingestion = ingestion
        self.provider_rate_limiter = provider_rate_limiter
        self.provider_rate_limit_policy = provider_rate_limit_policy

    async def backfill_source(
        self, *, workspace_id: str, source_connection_id: str
    ) -> SlackBackfillResult:
        source = await maybe_await(
            self.source_connections.get_by_id(source_connection_id)
        )
        job = await maybe_await(
            self.backfills.create(
                workspace_id=workspace_id, source_connection_id=source_connection_id
            )
        )
        await maybe_await(self.backfills.mark_running(job.id))
        cursor = await maybe_await(
            self.cursors.get_for_source(
                workspace_id=workspace_id, source_connection_id=source_connection_id
            )
        )
        raw_events_created = 0
        duplicates = 0
        latest_ts: str | None = cursor.cursor_value if cursor else None
        page_cursor: str | None = None
        installation = await maybe_await(
            self.installations.get_by_id(source.oauth_installation_id)
        )
        access_token = await maybe_await(
            self.secrets.get_token(installation.secret_ref_id)
        )
        try:
            while True:
                self._enforce_provider_limit(
                    workspace_id=workspace_id, operation="conversation_history"
                )
                page = await self.client.conversation_history(
                    access_token=access_token,
                    channel_id=source.external_source_id,
                    cursor=page_cursor,
                    oldest=cursor.cursor_value if cursor else None,
                )
                for message in sorted(
                    page.messages, key=lambda item: str(item.get("ts", ""))
                ):
                    created, duplicate = await self._persist_message_family(
                        workspace_id=workspace_id,
                        source_connection_id=source_connection_id,
                        message=message,
                    )
                    raw_events_created += created
                    duplicates += duplicate
                    latest_ts = str(message.get("ts") or latest_ts or "")
                    cursor = await maybe_await(
                        self.cursors.advance_after_persist(
                            workspace_id=workspace_id,
                            source_connection_id=source_connection_id,
                            event_ts=latest_ts,
                        )
                    )
                    if message.get("reply_count"):
                        self._enforce_provider_limit(
                            workspace_id=workspace_id, operation="thread_replies"
                        )
                        replies = await self.client.thread_replies(
                            access_token=access_token,
                            channel_id=source.external_source_id,
                            thread_ts=str(message.get("ts")),
                        )
                        for reply in sorted(
                            replies, key=lambda item: str(item.get("ts", ""))
                        ):
                            created, duplicate = await self._persist_message_family(
                                workspace_id=workspace_id,
                                source_connection_id=source_connection_id,
                                message=reply,
                            )
                            raw_events_created += created
                            duplicates += duplicate
                            latest_ts = str(reply.get("ts") or latest_ts or "")
                            cursor = await maybe_await(
                                self.cursors.advance_after_persist(
                                    workspace_id=workspace_id,
                                    source_connection_id=source_connection_id,
                                    event_ts=latest_ts,
                                )
                            )
                if not page.next_cursor:
                    break
                page_cursor = page.next_cursor
        except SlackRateLimitError:
            job = await maybe_await(
                self.backfills.mark_retrying(job.id, error_code="rate_limited")
            )
            return SlackBackfillResult(
                False, job, raw_events_created, duplicates, latest_ts
            )
        except RateLimitExceededError:
            job = await maybe_await(
                self.backfills.mark_retrying(job.id, error_code="rate_limited")
            )
            return SlackBackfillResult(
                False, job, raw_events_created, duplicates, latest_ts
            )
        except (SlackPermanentError, RawEventIdempotencyConflict):
            job = await maybe_await(
                self.backfills.mark_deadlettered(job.id, error_code="permanent_failure")
            )
            return SlackBackfillResult(
                False, job, raw_events_created, duplicates, latest_ts
            )

        job = await maybe_await(
            self.backfills.mark_completed(
                job.id,
                cursor_id=cursor.id if cursor else None,
            )
        )
        return SlackBackfillResult(True, job, raw_events_created, duplicates, latest_ts)

    def _enforce_provider_limit(self, *, workspace_id: str, operation: str) -> None:
        if not self.provider_rate_limiter or not self.provider_rate_limit_policy:
            return
        self.provider_rate_limiter.enforce(
            self.provider_rate_limit_policy,
            RateLimitSubject(
                workspace_id=workspace_id,
                user_id="provider:slack",
                client_id=f"slack:{operation}",
            ),
        )

    async def _persist_message_family(
        self,
        *,
        workspace_id: str,
        source_connection_id: str,
        message: dict[str, object],
    ) -> tuple[int, int]:
        source = await maybe_await(
            self.source_connections.get_by_id(source_connection_id)
        )
        created_count = 0
        duplicate_count = 0
        for raw_event in derived_raw_events_for_message(
            workspace_id=workspace_id,
            source=source,
            message=message,
        ):
            result = await self.ingestion.ingest(raw_event)
            if result.created:
                created_count += 1
            else:
                duplicate_count += 1
        return created_count, duplicate_count
