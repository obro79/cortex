from __future__ import annotations

from datetime import UTC, datetime

from cortex.contracts.entities import (
    BackfillJob,
    OAuthInstallation,
    ProviderCursor,
    SecretRef,
    SourceConnection,
    WebhookDelivery,
)
from cortex.contracts.enums import (
    BackfillJobStatus,
    OAuthInstallationStatus,
    ProviderCursorStatus,
    SecretRefStatus,
    SourceConnectionStatus,
    WebhookDeliveryStatus,
)
from cortex.ingestion.payloads import sha256_digest


class InMemorySecretRefRepository:
    def __init__(self) -> None:
        self._records: dict[str, SecretRef] = {}
        self._material: dict[str, str] = {}

    def create_for_token(
        self, *, workspace_id: str, provider: str, token: str
    ) -> SecretRef:
        now = datetime.now(UTC)
        digest = sha256_digest(token.encode()).removeprefix("sha256:")
        record = SecretRef(
            id=f"sec_{digest[:24]}",
            workspace_id=workspace_id,
            provider=provider,
            purpose="oauth_access_token",
            external_secret_id=f"local-secret:{digest[:32]}",
            key_version="local-v1",
            status=SecretRefStatus.ACTIVE,
            metadata_json={"token_hash": f"sha256:{digest}"},
            created_at=now,
            updated_at=now,
        )
        self._records[record.id] = record
        self._material[record.external_secret_id] = token
        return record

    def get_by_id(self, secret_ref_id: str) -> SecretRef:
        return self._records[secret_ref_id]

    def get_token(self, secret_ref_id: str) -> str:
        secret = self.get_by_id(secret_ref_id)
        return self._material[secret.external_secret_id]


class InMemoryOAuthInstallationRepository:
    def __init__(self) -> None:
        self._records: dict[str, OAuthInstallation] = {}
        self._by_workspace: dict[tuple[str, str, str], str] = {}

    def upsert_active(
        self,
        *,
        workspace_id: str,
        provider_workspace_id: str,
        secret_ref_id: str,
        scopes: set[str],
        status: OAuthInstallationStatus,
        health_json: dict[str, object],
        enterprise_id: str | None = None,
        bot_user_id: str | None = None,
        installing_actor_id: str | None = None,
        provider_metadata_json: dict[str, object] | None = None,
    ) -> OAuthInstallation:
        now = datetime.now(UTC)
        key = (workspace_id, "slack", provider_workspace_id)
        existing_id = self._by_workspace.get(key)
        scopes_json: dict[str, object] = {"scopes": sorted(scopes)}
        installed_at = now if status == OAuthInstallationStatus.ACTIVE else None
        update = {
            "secret_ref_id": secret_ref_id,
            "scopes_json": scopes_json,
            "status": status,
            "health_json": health_json,
            "enterprise_id": enterprise_id,
            "bot_user_id": bot_user_id,
            "installing_actor_id": installing_actor_id,
            "provider_metadata_json": provider_metadata_json or {},
            "installed_at": installed_at,
            "updated_at": now,
        }
        if existing_id is not None:
            updated = self._records[existing_id].model_copy(update=update)
            self._records[existing_id] = updated
            return updated
        record = OAuthInstallation(
            id=f"oauth_{sha256_digest(':'.join(key).encode()).removeprefix('sha256:')[:24]}",
            workspace_id=workspace_id,
            provider="slack",
            provider_workspace_id=provider_workspace_id,
            enterprise_id=enterprise_id,
            bot_user_id=bot_user_id,
            installing_actor_id=installing_actor_id,
            secret_ref_id=secret_ref_id,
            scopes_json=scopes_json,
            provider_metadata_json=provider_metadata_json or {},
            status=status,
            health_json=health_json,
            installed_at=installed_at,
            created_at=now,
            updated_at=now,
        )
        self._records[record.id] = record
        self._by_workspace[key] = record.id
        return record

    def get_by_id(self, installation_id: str) -> OAuthInstallation:
        return self._records[installation_id]

    def list_for_workspace(self, workspace_id: str) -> list[OAuthInstallation]:
        return [
            record
            for record in self._records.values()
            if record.workspace_id == workspace_id and record.provider == "slack"
        ]


class InMemorySourceConnectionRepository:
    def __init__(self) -> None:
        self._records: dict[str, SourceConnection] = {}
        self._by_source: dict[tuple[str, str, str], str] = {}

    def upsert_channel(
        self,
        *,
        workspace_id: str,
        oauth_installation_id: str,
        channel_id: str,
        display_name: str | None = None,
        status: SourceConnectionStatus = SourceConnectionStatus.ACTIVE,
    ) -> SourceConnection:
        now = datetime.now(UTC)
        key = (workspace_id, "slack", channel_id)
        existing_id = self._by_source.get(key)
        name_hash = sha256_digest(display_name.encode()) if display_name else None
        selected = status == SourceConnectionStatus.ACTIVE
        provider_metadata_json = {"source_kind": "slack_channel"}
        update = {
            "oauth_installation_id": oauth_installation_id,
            "display_name_hash": name_hash,
            "selected": selected,
            "status": status,
            "provider_metadata_json": provider_metadata_json,
            "updated_at": now,
        }
        if existing_id is not None:
            updated = self._records[existing_id].model_copy(update=update)
            self._records[existing_id] = updated
            return updated
        record = SourceConnection(
            id=f"srcconn_{sha256_digest(':'.join(key).encode()).removeprefix('sha256:')[:24]}",
            workspace_id=workspace_id,
            provider="slack",
            oauth_installation_id=oauth_installation_id,
            source_type="channel",
            external_source_id=channel_id,
            display_name_hash=name_hash,
            selected=selected,
            status=status,
            provider_metadata_json=provider_metadata_json,
            created_at=now,
            updated_at=now,
        )
        self._records[record.id] = record
        self._by_source[key] = record.id
        return record

    def get_selected_channel(
        self, workspace_id: str, channel_id: str
    ) -> SourceConnection | None:
        record_id = self._by_source.get((workspace_id, "slack", channel_id))
        if record_id is None:
            return None
        record = self._records[record_id]
        if record.status != SourceConnectionStatus.ACTIVE or not record.selected:
            return None
        return record

    def list_selected(self, workspace_id: str) -> list[SourceConnection]:
        return [
            record
            for record in self._records.values()
            if record.workspace_id == workspace_id
            and record.provider == "slack"
            and record.selected
            and record.status == SourceConnectionStatus.ACTIVE
        ]

    def get_by_id(self, source_connection_id: str) -> SourceConnection:
        return self._records[source_connection_id]


class InMemoryWebhookDeliveryRepository:
    def __init__(self) -> None:
        self._records: dict[str, WebhookDelivery] = {}
        self._by_delivery: dict[tuple[str, str, str], str] = {}

    def create_or_duplicate(
        self,
        *,
        workspace_id: str,
        delivery_id: str,
        event_id: str | None,
        signature_status: str,
    ) -> tuple[WebhookDelivery, bool]:
        now = datetime.now(UTC)
        key = (workspace_id, "slack", delivery_id)
        existing_id = self._by_delivery.get(key)
        if existing_id is not None:
            existing = self._records[existing_id]
            duplicate = existing.model_copy(
                update={
                    "status": WebhookDeliveryStatus.IGNORED_DUPLICATE,
                    "updated_at": now,
                }
            )
            self._records[existing_id] = duplicate
            return duplicate, False
        record = WebhookDelivery(
            id=f"wh_{sha256_digest(':'.join(key).encode()).removeprefix('sha256:')[:24]}",
            workspace_id=workspace_id,
            provider="slack",
            delivery_id=delivery_id,
            event_id=event_id,
            signature_status=signature_status,
            status=WebhookDeliveryStatus.RECEIVED,
            received_at=now,
            updated_at=now,
        )
        self._records[record.id] = record
        self._by_delivery[key] = record.id
        return record, True

    def mark_persisted(
        self,
        delivery_id: str,
        *,
        source_connection_id: str | None = None,
        raw_event_id: str | None = None,
    ) -> WebhookDelivery:
        record = self._records[delivery_id]
        updated = record.model_copy(
            update={
                "status": WebhookDeliveryStatus.PERSISTED,
                "source_connection_id": source_connection_id,
                "raw_event_id": raw_event_id,
                "updated_at": datetime.now(UTC),
            }
        )
        self._records[delivery_id] = updated
        return updated


class InMemoryProviderCursorRepository:
    def __init__(self) -> None:
        self._records: dict[str, ProviderCursor] = {}

    def advance_after_persist(
        self, *, source_connection_id: str, workspace_id: str, event_ts: str
    ) -> ProviderCursor:
        now = datetime.now(UTC)
        identity = f"{workspace_id}:{source_connection_id}:history"
        cursor_id = (
            "cursor_" + sha256_digest(identity.encode()).removeprefix("sha256:")[:24]
        )
        existing = self._records.get(cursor_id)
        record = ProviderCursor(
            id=cursor_id,
            workspace_id=workspace_id,
            provider="slack",
            source_connection_id=source_connection_id,
            cursor_type="history",
            cursor_value=event_ts,
            high_watermark=event_ts,
            status=ProviderCursorStatus.ACTIVE,
            last_advanced_at=now,
            metadata_json={},
            created_at=existing.created_at if existing else now,
            updated_at=now,
        )
        self._records[cursor_id] = record
        return record

    def get_for_source(
        self, *, workspace_id: str, source_connection_id: str
    ) -> ProviderCursor | None:
        identity = f"{workspace_id}:{source_connection_id}:history"
        cursor_id = (
            "cursor_" + sha256_digest(identity.encode()).removeprefix("sha256:")[:24]
        )
        return self._records.get(cursor_id)


class InMemoryBackfillJobRepository:
    def __init__(self) -> None:
        self._records: dict[str, BackfillJob] = {}

    def create(self, *, workspace_id: str, source_connection_id: str) -> BackfillJob:
        now = datetime.now(UTC)
        job = BackfillJob(
            id=f"bf_{sha256_digest(f'{workspace_id}:{source_connection_id}:{now.isoformat()}'.encode()).removeprefix('sha256:')[:24]}",
            workspace_id=workspace_id,
            provider="slack",
            source_connection_id=source_connection_id,
            status=BackfillJobStatus.QUEUED,
            metadata_json={},
            created_at=now,
            updated_at=now,
        )
        self._records[job.id] = job
        return job

    def mark_running(self, job_id: str) -> BackfillJob:
        job = self._records[job_id]
        updated = job.model_copy(
            update={
                "status": BackfillJobStatus.RUNNING,
                "started_at": datetime.now(UTC),
                "updated_at": datetime.now(UTC),
            }
        )
        self._records[job_id] = updated
        return updated

    def mark_completed(self, job_id: str, *, cursor_id: str | None) -> BackfillJob:
        job = self._records[job_id]
        now = datetime.now(UTC)
        updated = job.model_copy(
            update={
                "status": BackfillJobStatus.COMPLETED,
                "cursor_id": cursor_id,
                "completed_at": now,
                "updated_at": now,
            }
        )
        self._records[job_id] = updated
        return updated

    def mark_retrying(self, job_id: str, *, error_code: str) -> BackfillJob:
        job = self._records[job_id]
        updated = job.model_copy(
            update={
                "status": BackfillJobStatus.RETRYING,
                "attempt_count": job.attempt_count + 1,
                "last_error_code": error_code,
                "updated_at": datetime.now(UTC),
            }
        )
        self._records[job_id] = updated
        return updated

    def mark_deadlettered(self, job_id: str, *, error_code: str) -> BackfillJob:
        job = self._records[job_id]
        updated = job.model_copy(
            update={
                "status": BackfillJobStatus.DEADLETTERED,
                "attempt_count": job.attempt_count + 1,
                "last_error_code": error_code,
                "updated_at": datetime.now(UTC),
            }
        )
        self._records[job_id] = updated
        return updated

    def list_for_workspace(self, workspace_id: str) -> list[BackfillJob]:
        return [
            job for job in self._records.values() if job.workspace_id == workspace_id
        ]
