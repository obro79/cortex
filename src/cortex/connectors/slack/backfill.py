from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from cortex.contracts.entities import BackfillJob
from cortex.ingestion.raw_events import RawEventIdempotencyConflict, RawEventInput
from cortex.ingestion.service import IngestionResult

from .client import SlackPermanentError, SlackRateLimitError, SlackWebClient
from .mapping import derived_raw_events_for_message
from .repositories import (
    InMemoryBackfillJobRepository,
    InMemoryOAuthInstallationRepository,
    InMemoryProviderCursorRepository,
    InMemorySecretRefRepository,
    InMemorySourceConnectionRepository,
)


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
        source_connections: InMemorySourceConnectionRepository,
        installations: InMemoryOAuthInstallationRepository,
        secrets: InMemorySecretRefRepository,
        cursors: InMemoryProviderCursorRepository,
        backfills: InMemoryBackfillJobRepository,
        ingestion: SlackBackfillIngestionService,
    ) -> None:
        self.client = client
        self.source_connections = source_connections
        self.installations = installations
        self.secrets = secrets
        self.cursors = cursors
        self.backfills = backfills
        self.ingestion = ingestion

    async def backfill_source(
        self, *, workspace_id: str, source_connection_id: str
    ) -> SlackBackfillResult:
        source = self.source_connections.get_by_id(source_connection_id)
        job = self.backfills.create(
            workspace_id=workspace_id, source_connection_id=source_connection_id
        )
        self.backfills.mark_running(job.id)
        cursor = self.cursors.get_for_source(
            workspace_id=workspace_id, source_connection_id=source_connection_id
        )
        raw_events_created = 0
        duplicates = 0
        latest_ts: str | None = cursor.cursor_value if cursor else None
        page_cursor: str | None = None
        installation = self.installations.get_by_id(source.oauth_installation_id)
        access_token = self.secrets.get_token(installation.secret_ref_id)
        try:
            while True:
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
                    cursor = self.cursors.advance_after_persist(
                        workspace_id=workspace_id,
                        source_connection_id=source_connection_id,
                        event_ts=latest_ts,
                    )
                    if message.get("reply_count"):
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
                            cursor = self.cursors.advance_after_persist(
                                workspace_id=workspace_id,
                                source_connection_id=source_connection_id,
                                event_ts=latest_ts,
                            )
                if not page.next_cursor:
                    break
                page_cursor = page.next_cursor
        except SlackRateLimitError:
            job = self.backfills.mark_retrying(job.id, error_code="rate_limited")
            return SlackBackfillResult(
                False, job, raw_events_created, duplicates, latest_ts
            )
        except (SlackPermanentError, RawEventIdempotencyConflict):
            job = self.backfills.mark_deadlettered(
                job.id, error_code="permanent_failure"
            )
            return SlackBackfillResult(
                False, job, raw_events_created, duplicates, latest_ts
            )

        job = self.backfills.mark_completed(
            job.id,
            cursor_id=cursor.id if cursor else None,
        )
        return SlackBackfillResult(True, job, raw_events_created, duplicates, latest_ts)

    async def _persist_message_family(
        self,
        *,
        workspace_id: str,
        source_connection_id: str,
        message: dict[str, object],
    ) -> tuple[int, int]:
        source = self.source_connections.get_by_id(source_connection_id)
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
