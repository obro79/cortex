from __future__ import annotations

from cortex.contracts.enums import BackfillJobStatus, OAuthInstallationStatus

from .repositories import (
    InMemoryBackfillJobRepository,
    InMemoryOAuthInstallationRepository,
    InMemoryProviderCursorRepository,
    InMemorySourceConnectionRepository,
)


class SlackHealthService:
    def __init__(
        self,
        *,
        installations: InMemoryOAuthInstallationRepository,
        source_connections: InMemorySourceConnectionRepository,
        cursors: InMemoryProviderCursorRepository,
        backfills: InMemoryBackfillJobRepository,
    ) -> None:
        self.installations = installations
        self.source_connections = source_connections
        self.cursors = cursors
        self.backfills = backfills

    def workspace_health(self, workspace_id: str) -> dict[str, object]:
        selected = self.source_connections.list_selected(workspace_id)
        jobs = self.backfills.list_for_workspace(workspace_id)
        deadletters = [
            job for job in jobs if job.status == BackfillJobStatus.DEADLETTERED
        ]
        retrying = [job for job in jobs if job.status == BackfillJobStatus.RETRYING]
        cursors = [
            self.cursors.get_for_source(
                workspace_id=workspace_id, source_connection_id=source.id
            )
            for source in selected
        ]
        active_cursors = [cursor for cursor in cursors if cursor is not None]
        return {
            "provider": "slack",
            "selected_channel_count": len(selected),
            "cursor_count": len(active_cursors),
            "newest_cursor": max(
                (cursor.high_watermark or "" for cursor in active_cursors),
                default=None,
            ),
            "deadletter_count": len(deadletters),
            "retrying_count": len(retrying),
            "oauth_status": OAuthInstallationStatus.ACTIVE,
        }
