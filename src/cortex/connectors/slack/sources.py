from __future__ import annotations

from typing import Any

from cortex.utils.asyncio import maybe_await

from .client import SlackWebClient


class SlackSourceSelectionService:
    def __init__(
        self,
        *,
        installations: Any,
        secrets: Any,
        source_connections: Any,
        client: SlackWebClient,
    ) -> None:
        self.installations = installations
        self.secrets = secrets
        self.source_connections = source_connections
        self.client = client

    async def list_channels(
        self,
        *,
        workspace_id: str,
        oauth_installation_id: str,
        cursor: str | None = None,
    ) -> dict[str, object]:
        installation = await maybe_await(
            self.installations.get_by_id(oauth_installation_id)
        )
        if installation.workspace_id != workspace_id:
            raise PermissionError("workspace_mismatch")
        access_token = await maybe_await(
            self.secrets.get_token(installation.secret_ref_id)
        )
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

    async def require_installation_workspace(
        self, *, workspace_id: str, oauth_installation_id: str
    ) -> None:
        installation = await maybe_await(
            self.installations.get_by_id(oauth_installation_id)
        )
        if installation.workspace_id != workspace_id:
            raise PermissionError("workspace_mismatch")

    async def select_channels(
        self,
        *,
        workspace_id: str,
        oauth_installation_id: str,
        channels: list[dict[str, str]],
    ) -> dict[str, object]:
        installation = await maybe_await(
            self.installations.get_by_id(oauth_installation_id)
        )
        if installation.workspace_id != workspace_id:
            raise PermissionError("workspace_mismatch")
        selected = []
        for channel in channels:
            selected.append(
                await maybe_await(
                    self.source_connections.upsert_channel(
                        workspace_id=installation.workspace_id,
                        oauth_installation_id=oauth_installation_id,
                        channel_id=channel["id"],
                        display_name=channel.get("name"),
                        provider_metadata_json={
                            "source_kind": "slack_channel",
                            "team_id": installation.provider_workspace_id,
                        },
                    )
                )
            )
        return {
            "ok": True,
            "source_connections": [
                source.model_dump(mode="json") for source in selected
            ],
        }

    async def deselect_channel(
        self, *, workspace_id: str, source_connection_id: str
    ) -> dict[str, object]:
        source = await maybe_await(
            self.source_connections.get_by_id(source_connection_id)
        )
        if source.workspace_id != workspace_id:
            raise PermissionError("workspace_mismatch")
        disabled = await maybe_await(
            self.source_connections.disable_channel(
                workspace_id=workspace_id, source_connection_id=source_connection_id
            )
        )
        return {
            "ok": True,
            "status": "disabled",
            "source_connection": disabled.model_dump(mode="json"),
        }
