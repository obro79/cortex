from __future__ import annotations

from .repositories import (
    InMemoryOAuthInstallationRepository,
    InMemorySourceConnectionRepository,
)


class SlackSourceSelectionService:
    def __init__(
        self,
        *,
        installations: InMemoryOAuthInstallationRepository,
        source_connections: InMemorySourceConnectionRepository,
    ) -> None:
        self.installations = installations
        self.source_connections = source_connections

    def select_channels(
        self,
        *,
        workspace_id: str,
        oauth_installation_id: str,
        channels: list[dict[str, str]],
    ) -> dict[str, object]:
        self.installations.get_by_id(oauth_installation_id)
        selected = [
            self.source_connections.upsert_channel(
                workspace_id=workspace_id,
                oauth_installation_id=oauth_installation_id,
                channel_id=channel["id"],
                display_name=channel.get("name"),
            )
            for channel in channels
        ]
        return {
            "ok": True,
            "source_connections": [
                source.model_dump(mode="json") for source in selected
            ],
        }
