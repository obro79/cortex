from __future__ import annotations

from .client import SlackWebClient
from .repositories import (
    InMemoryOAuthInstallationRepository,
    InMemorySecretRefRepository,
    InMemorySourceConnectionRepository,
)


class SlackSourceSelectionService:
    def __init__(
        self,
        *,
        installations: InMemoryOAuthInstallationRepository,
        secrets: InMemorySecretRefRepository,
        source_connections: InMemorySourceConnectionRepository,
        client: SlackWebClient,
    ) -> None:
        self.installations = installations
        self.secrets = secrets
        self.source_connections = source_connections
        self.client = client

    async def list_channels(
        self, *, oauth_installation_id: str, cursor: str | None = None
    ) -> dict[str, object]:
        installation = self.installations.get_by_id(oauth_installation_id)
        access_token = self.secrets.get_token(installation.secret_ref_id)
        page = await self.client.conversations_list(
            access_token=access_token,
            cursor=cursor,
        )
        channels = [
            {
                "id": str(channel.get("id", "")),
                "name": str(channel.get("name", "")),
                "is_private": bool(channel.get("is_private", False)),
                "is_member": bool(channel.get("is_member", False)),
            }
            for channel in page.messages
            if channel.get("id")
        ]
        return {"ok": True, "channels": channels, "next_cursor": page.next_cursor}

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
