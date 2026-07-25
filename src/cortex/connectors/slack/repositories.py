from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

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
from cortex.db.models import (
    BackfillJobRecord,
    OAuthInstallationRecord,
    ProviderCursorRecord,
    SecretMaterialRecord,
    SecretRefRecord,
    SourceConnectionRecord,
    WebhookDeliveryRecord,
)
from cortex.ingestion.payloads import sha256_digest
from cortex.security.tokens import TokenCipher


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

    def get_active_by_provider_workspace_id(
        self, provider_workspace_id: str
    ) -> OAuthInstallation | None:
        for record in self._records.values():
            if (
                record.provider == "slack"
                and record.provider_workspace_id == provider_workspace_id
                and record.status == OAuthInstallationStatus.ACTIVE
            ):
                return record
        return None


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
        provider_metadata_json: dict[str, object] | None = None,
        status: SourceConnectionStatus = SourceConnectionStatus.ACTIVE,
    ) -> SourceConnection:
        now = datetime.now(UTC)
        key = (workspace_id, "slack", channel_id)
        existing_id = self._by_source.get(key)
        name_hash = sha256_digest(display_name.encode()) if display_name else None
        selected = status == SourceConnectionStatus.ACTIVE
        provider_metadata_json = provider_metadata_json or {
            "source_kind": "slack_channel"
        }
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

    def disable_channel(
        self, *, workspace_id: str, source_connection_id: str
    ) -> SourceConnection:
        record = self.get_by_id(source_connection_id)
        if record.workspace_id != workspace_id or record.provider != "slack":
            raise PermissionError("workspace_mismatch")
        updated = record.model_copy(
            update={
                "selected": False,
                "status": SourceConnectionStatus.DISABLED,
                "updated_at": datetime.now(UTC),
            }
        )
        self._records[source_connection_id] = updated
        return updated


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


def secret_ref_from_record(record: SecretRefRecord) -> SecretRef:
    return SecretRef(
        id=record.id,
        workspace_id=record.workspace_id,
        provider=record.provider,
        purpose=record.purpose,
        external_secret_id=record.external_secret_id,
        key_version=record.key_version,
        status=SecretRefStatus(record.status),
        metadata_json=record.metadata_json,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def oauth_installation_from_record(
    record: OAuthInstallationRecord,
) -> OAuthInstallation:
    return OAuthInstallation(
        id=record.id,
        workspace_id=record.workspace_id,
        provider=record.provider,
        provider_workspace_id=record.provider_workspace_id,
        enterprise_id=record.enterprise_id,
        bot_user_id=record.bot_user_id,
        installing_actor_id=record.installing_actor_id,
        secret_ref_id=record.secret_ref_id,
        scopes_json=record.scopes_json,
        provider_metadata_json=record.provider_metadata_json,
        status=OAuthInstallationStatus(record.status),
        health_json=record.health_json,
        installed_at=record.installed_at,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def source_connection_from_record(record: SourceConnectionRecord) -> SourceConnection:
    return SourceConnection(
        id=record.id,
        workspace_id=record.workspace_id,
        provider=record.provider,
        oauth_installation_id=record.oauth_installation_id,
        source_type=record.source_type,
        external_source_id=record.external_source_id,
        display_name_hash=record.display_name_hash,
        selected=record.selected,
        status=SourceConnectionStatus(record.status),
        provider_metadata_json=record.provider_metadata_json,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def webhook_delivery_from_record(record: WebhookDeliveryRecord) -> WebhookDelivery:
    return WebhookDelivery(
        id=record.id,
        workspace_id=record.workspace_id,
        provider=record.provider,
        delivery_id=record.delivery_id,
        event_id=record.event_id,
        signature_status=record.signature_status,
        status=WebhookDeliveryStatus(record.status),
        source_connection_id=record.source_connection_id,
        raw_event_id=record.raw_event_id,
        received_at=record.received_at,
        updated_at=record.updated_at,
        error_code=record.error_code,
        trace_id=record.trace_id,
    )


def backfill_job_from_record(record: BackfillJobRecord) -> BackfillJob:
    return BackfillJob(
        id=record.id,
        workspace_id=record.workspace_id,
        provider=record.provider,
        source_connection_id=record.source_connection_id,
        status=BackfillJobStatus(record.status),
        cursor_id=record.cursor_id,
        started_at=record.started_at,
        completed_at=record.completed_at,
        attempt_count=record.attempt_count,
        last_error_code=record.last_error_code,
        metadata_json=record.metadata_json,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def provider_cursor_from_record(record: ProviderCursorRecord) -> ProviderCursor:
    return ProviderCursor(
        id=record.id,
        workspace_id=record.workspace_id,
        provider=record.provider,
        source_connection_id=record.source_connection_id,
        cursor_type=record.cursor_type,
        cursor_value=record.cursor_value,
        high_watermark=record.high_watermark,
        status=ProviderCursorStatus(record.status),
        last_advanced_at=record.last_advanced_at,
        metadata_json=record.metadata_json,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


class SqlAlchemySecretRefRepository:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        cipher: TokenCipher,
        key_version: str,
    ) -> None:
        self.session_factory = session_factory
        self.cipher = cipher
        self.key_version = key_version

    async def create_for_token(
        self, *, workspace_id: str, provider: str, token: str
    ) -> SecretRef:
        now = datetime.now(UTC)
        digest = sha256_digest(token.encode()).removeprefix("sha256:")
        secret_id = f"sec_{digest[:24]}"
        encrypted = self.cipher.encrypt(token)
        async with self.session_factory() as session:
            existing = await session.get(SecretRefRecord, secret_id)
            if existing is None:
                existing = SecretRefRecord(
                    id=secret_id,
                    workspace_id=workspace_id,
                    provider=provider,
                    purpose="oauth_access_token",
                    external_secret_id=f"sql-secret:{secret_id}",
                    key_version=self.key_version,
                    status=SecretRefStatus.ACTIVE.value,
                    metadata_json={"token_hash": f"sha256:{digest}"},
                    created_at=now,
                    updated_at=now,
                )
                session.add(existing)
            else:
                existing.status = SecretRefStatus.ACTIVE.value
                existing.key_version = self.key_version
                existing.metadata_json = {"token_hash": f"sha256:{digest}"}
                existing.updated_at = now
            material = await self._get_material(session, secret_id)
            if material is None:
                material = SecretMaterialRecord(
                    id=f"mat_{secret_id}",
                    secret_ref_id=secret_id,
                    workspace_id=workspace_id,
                    provider=provider,
                    encryption_scheme=self.cipher.encryption_scheme,
                    key_version=self.key_version,
                    ciphertext=encrypted,
                    created_at=now,
                    updated_at=now,
                )
                session.add(material)
            else:
                material.encryption_scheme = self.cipher.encryption_scheme
                material.key_version = self.key_version
                material.ciphertext = encrypted
                material.updated_at = now
            await session.commit()
            await session.refresh(existing)
            return secret_ref_from_record(existing)

    async def get_by_id(self, secret_ref_id: str) -> SecretRef:
        async with self.session_factory() as session:
            record = await session.get(SecretRefRecord, secret_ref_id)
            if record is None:
                raise KeyError(secret_ref_id)
            return secret_ref_from_record(record)

    async def get_token(self, secret_ref_id: str) -> str:
        async with self.session_factory() as session:
            material = await self._get_material(session, secret_ref_id)
            if material is None:
                raise KeyError(secret_ref_id)
            return self.cipher.decrypt(material.ciphertext)

    async def _get_material(
        self, session: AsyncSession, secret_ref_id: str
    ) -> SecretMaterialRecord | None:
        result = await session.execute(
            select(SecretMaterialRecord).where(
                SecretMaterialRecord.secret_ref_id == secret_ref_id
            )
        )
        return result.scalar_one_or_none()


class SqlAlchemyOAuthInstallationRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self.session_factory = session_factory

    async def upsert_active(
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
        scopes_json: dict[str, object] = {"scopes": sorted(scopes)}
        installed_at = now if status == OAuthInstallationStatus.ACTIVE else None
        async with self.session_factory() as session:
            result = await session.execute(
                select(OAuthInstallationRecord).where(
                    OAuthInstallationRecord.workspace_id == workspace_id,
                    OAuthInstallationRecord.provider == "slack",
                    OAuthInstallationRecord.provider_workspace_id
                    == provider_workspace_id,
                )
            )
            record = result.scalar_one_or_none()
            if record is None:
                record = OAuthInstallationRecord(
                    id=f"oauth_{sha256_digest(':'.join(key).encode()).removeprefix('sha256:')[:24]}",
                    workspace_id=workspace_id,
                    provider="slack",
                    provider_workspace_id=provider_workspace_id,
                    created_at=now,
                    updated_at=now,
                )
                session.add(record)
            record.enterprise_id = enterprise_id
            record.bot_user_id = bot_user_id
            record.installing_actor_id = installing_actor_id
            record.secret_ref_id = secret_ref_id
            record.scopes_json = scopes_json
            record.provider_metadata_json = provider_metadata_json or {}
            record.status = status.value
            record.health_json = health_json
            record.installed_at = installed_at
            record.updated_at = now
            await session.commit()
            await session.refresh(record)
            return oauth_installation_from_record(record)

    async def get_by_id(self, installation_id: str) -> OAuthInstallation:
        async with self.session_factory() as session:
            record = await session.get(OAuthInstallationRecord, installation_id)
            if record is None:
                raise KeyError(installation_id)
            return oauth_installation_from_record(record)

    async def list_for_workspace(self, workspace_id: str) -> list[OAuthInstallation]:
        async with self.session_factory() as session:
            result = await session.execute(
                select(OAuthInstallationRecord).where(
                    OAuthInstallationRecord.workspace_id == workspace_id,
                    OAuthInstallationRecord.provider == "slack",
                )
            )
            return [
                oauth_installation_from_record(record) for record in result.scalars()
            ]

    async def get_active_by_provider_workspace_id(
        self, provider_workspace_id: str
    ) -> OAuthInstallation | None:
        async with self.session_factory() as session:
            result = await session.execute(
                select(OAuthInstallationRecord).where(
                    OAuthInstallationRecord.provider == "slack",
                    OAuthInstallationRecord.provider_workspace_id
                    == provider_workspace_id,
                    OAuthInstallationRecord.status
                    == OAuthInstallationStatus.ACTIVE.value,
                )
            )
            record = result.scalar_one_or_none()
            return oauth_installation_from_record(record) if record else None


class SqlAlchemySourceConnectionRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self.session_factory = session_factory

    async def upsert_channel(
        self,
        *,
        workspace_id: str,
        oauth_installation_id: str,
        channel_id: str,
        display_name: str | None = None,
        provider_metadata_json: dict[str, object] | None = None,
        status: SourceConnectionStatus = SourceConnectionStatus.ACTIVE,
    ) -> SourceConnection:
        now = datetime.now(UTC)
        key = (workspace_id, "slack", channel_id)
        name_hash = sha256_digest(display_name.encode()) if display_name else None
        async with self.session_factory() as session:
            result = await session.execute(
                select(SourceConnectionRecord).where(
                    SourceConnectionRecord.workspace_id == workspace_id,
                    SourceConnectionRecord.provider == "slack",
                    SourceConnectionRecord.external_source_id == channel_id,
                )
            )
            record = result.scalar_one_or_none()
            if record is None:
                record = SourceConnectionRecord(
                    id=f"srcconn_{sha256_digest(':'.join(key).encode()).removeprefix('sha256:')[:24]}",
                    workspace_id=workspace_id,
                    provider="slack",
                    source_type="channel",
                    external_source_id=channel_id,
                    created_at=now,
                    updated_at=now,
                )
                session.add(record)
            record.oauth_installation_id = oauth_installation_id
            record.display_name_hash = name_hash
            record.selected = status == SourceConnectionStatus.ACTIVE
            record.status = status.value
            record.provider_metadata_json = provider_metadata_json or {
                "source_kind": "slack_channel"
            }
            record.updated_at = now
            await session.commit()
            await session.refresh(record)
            return source_connection_from_record(record)

    async def get_selected_channel(
        self, workspace_id: str, channel_id: str
    ) -> SourceConnection | None:
        async with self.session_factory() as session:
            result = await session.execute(
                select(SourceConnectionRecord).where(
                    SourceConnectionRecord.workspace_id == workspace_id,
                    SourceConnectionRecord.provider == "slack",
                    SourceConnectionRecord.external_source_id == channel_id,
                    SourceConnectionRecord.selected.is_(True),
                    SourceConnectionRecord.status
                    == SourceConnectionStatus.ACTIVE.value,
                )
            )
            record = result.scalar_one_or_none()
            return source_connection_from_record(record) if record else None

    async def list_selected(self, workspace_id: str) -> list[SourceConnection]:
        async with self.session_factory() as session:
            result = await session.execute(
                select(SourceConnectionRecord).where(
                    SourceConnectionRecord.workspace_id == workspace_id,
                    SourceConnectionRecord.provider == "slack",
                    SourceConnectionRecord.selected.is_(True),
                    SourceConnectionRecord.status
                    == SourceConnectionStatus.ACTIVE.value,
                )
            )
            return [
                source_connection_from_record(record) for record in result.scalars()
            ]

    async def get_by_id(self, source_connection_id: str) -> SourceConnection:
        async with self.session_factory() as session:
            record = await session.get(SourceConnectionRecord, source_connection_id)
            if record is None:
                raise KeyError(source_connection_id)
            return source_connection_from_record(record)

    async def disable_channel(
        self, *, workspace_id: str, source_connection_id: str
    ) -> SourceConnection:
        async with self.session_factory() as session:
            record = await session.get(SourceConnectionRecord, source_connection_id)
            if record is None:
                raise KeyError(source_connection_id)
            if record.workspace_id != workspace_id or record.provider != "slack":
                raise PermissionError("workspace_mismatch")
            record.selected = False
            record.status = SourceConnectionStatus.DISABLED.value
            record.updated_at = datetime.now(UTC)
            await session.commit()
            await session.refresh(record)
            return source_connection_from_record(record)


class SqlAlchemyWebhookDeliveryRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self.session_factory = session_factory

    async def create_or_duplicate(
        self,
        *,
        workspace_id: str,
        delivery_id: str,
        event_id: str | None,
        signature_status: str,
    ) -> tuple[WebhookDelivery, bool]:
        now = datetime.now(UTC)
        key = (workspace_id, "slack", delivery_id)
        async with self.session_factory() as session:
            result = await session.execute(
                select(WebhookDeliveryRecord).where(
                    WebhookDeliveryRecord.workspace_id == workspace_id,
                    WebhookDeliveryRecord.provider == "slack",
                    WebhookDeliveryRecord.delivery_id == delivery_id,
                )
            )
            record = result.scalar_one_or_none()
            if record is not None:
                record.status = WebhookDeliveryStatus.IGNORED_DUPLICATE.value
                record.updated_at = now
                await session.commit()
                await session.refresh(record)
                return webhook_delivery_from_record(record), False
            record = WebhookDeliveryRecord(
                id=f"wh_{sha256_digest(':'.join(key).encode()).removeprefix('sha256:')[:24]}",
                workspace_id=workspace_id,
                provider="slack",
                delivery_id=delivery_id,
                event_id=event_id,
                signature_status=signature_status,
                status=WebhookDeliveryStatus.RECEIVED.value,
                received_at=now,
                updated_at=now,
            )
            session.add(record)
            await session.commit()
            await session.refresh(record)
            return webhook_delivery_from_record(record), True

    async def mark_persisted(
        self,
        delivery_id: str,
        *,
        source_connection_id: str | None = None,
        raw_event_id: str | None = None,
    ) -> WebhookDelivery:
        async with self.session_factory() as session:
            record = await session.get(WebhookDeliveryRecord, delivery_id)
            if record is None:
                raise KeyError(delivery_id)
            record.status = WebhookDeliveryStatus.PERSISTED.value
            record.source_connection_id = source_connection_id
            record.raw_event_id = raw_event_id
            record.updated_at = datetime.now(UTC)
            await session.commit()
            await session.refresh(record)
            return webhook_delivery_from_record(record)


class SqlAlchemyProviderCursorRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self.session_factory = session_factory

    async def advance_after_persist(
        self, *, source_connection_id: str, workspace_id: str, event_ts: str
    ) -> ProviderCursor:
        now = datetime.now(UTC)
        identity = f"{workspace_id}:{source_connection_id}:history"
        cursor_id = (
            "cursor_" + sha256_digest(identity.encode()).removeprefix("sha256:")[:24]
        )
        async with self.session_factory() as session:
            record = await session.get(ProviderCursorRecord, cursor_id)
            if record is None:
                record = ProviderCursorRecord(
                    id=cursor_id,
                    workspace_id=workspace_id,
                    provider="slack",
                    source_connection_id=source_connection_id,
                    cursor_type="history",
                    created_at=now,
                    updated_at=now,
                )
                session.add(record)
            record.cursor_value = event_ts
            record.high_watermark = event_ts
            record.status = ProviderCursorStatus.ACTIVE.value
            record.last_advanced_at = now
            record.metadata_json = {}
            record.updated_at = now
            await session.commit()
            await session.refresh(record)
            return provider_cursor_from_record(record)

    async def get_for_source(
        self, *, workspace_id: str, source_connection_id: str
    ) -> ProviderCursor | None:
        identity = f"{workspace_id}:{source_connection_id}:history"
        cursor_id = (
            "cursor_" + sha256_digest(identity.encode()).removeprefix("sha256:")[:24]
        )
        async with self.session_factory() as session:
            record = await session.get(ProviderCursorRecord, cursor_id)
            return provider_cursor_from_record(record) if record else None


class SqlAlchemyBackfillJobRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self.session_factory = session_factory

    async def create(
        self, *, workspace_id: str, source_connection_id: str
    ) -> BackfillJob:
        now = datetime.now(UTC)
        record = BackfillJobRecord(
            id=f"bf_{sha256_digest(f'{workspace_id}:{source_connection_id}:{now.isoformat()}'.encode()).removeprefix('sha256:')[:24]}",
            workspace_id=workspace_id,
            provider="slack",
            source_connection_id=source_connection_id,
            status=BackfillJobStatus.QUEUED.value,
            attempt_count=0,
            metadata_json={},
            created_at=now,
            updated_at=now,
        )
        async with self.session_factory() as session:
            session.add(record)
            await session.commit()
            await session.refresh(record)
            return backfill_job_from_record(record)

    async def mark_running(self, job_id: str) -> BackfillJob:
        return await self._update(
            job_id,
            status=BackfillJobStatus.RUNNING,
            started_at=datetime.now(UTC),
        )

    async def mark_completed(
        self, job_id: str, *, cursor_id: str | None
    ) -> BackfillJob:
        return await self._update(
            job_id,
            status=BackfillJobStatus.COMPLETED,
            cursor_id=cursor_id,
            completed_at=datetime.now(UTC),
        )

    async def mark_retrying(self, job_id: str, *, error_code: str) -> BackfillJob:
        async with self.session_factory() as session:
            record = await self._get_record(session, job_id)
            record.status = BackfillJobStatus.RETRYING.value
            record.attempt_count += 1
            record.last_error_code = error_code
            record.updated_at = datetime.now(UTC)
            await session.commit()
            await session.refresh(record)
            return backfill_job_from_record(record)

    async def mark_deadlettered(self, job_id: str, *, error_code: str) -> BackfillJob:
        async with self.session_factory() as session:
            record = await self._get_record(session, job_id)
            record.status = BackfillJobStatus.DEADLETTERED.value
            record.attempt_count += 1
            record.last_error_code = error_code
            record.updated_at = datetime.now(UTC)
            await session.commit()
            await session.refresh(record)
            return backfill_job_from_record(record)

    async def list_for_workspace(self, workspace_id: str) -> list[BackfillJob]:
        async with self.session_factory() as session:
            result = await session.execute(
                select(BackfillJobRecord).where(
                    BackfillJobRecord.workspace_id == workspace_id
                )
            )
            return [backfill_job_from_record(record) for record in result.scalars()]

    async def _update(
        self,
        job_id: str,
        *,
        status: BackfillJobStatus,
        cursor_id: str | None = None,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
    ) -> BackfillJob:
        async with self.session_factory() as session:
            record = await self._get_record(session, job_id)
            record.status = status.value
            if cursor_id is not None:
                record.cursor_id = cursor_id
            if started_at is not None:
                record.started_at = started_at
            if completed_at is not None:
                record.completed_at = completed_at
            record.updated_at = datetime.now(UTC)
            await session.commit()
            await session.refresh(record)
            return backfill_job_from_record(record)

    async def _get_record(
        self, session: AsyncSession, job_id: str
    ) -> BackfillJobRecord:
        record = await session.get(BackfillJobRecord, job_id)
        if record is None:
            raise KeyError(job_id)
        return record
