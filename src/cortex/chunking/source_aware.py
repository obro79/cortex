from __future__ import annotations

from datetime import UTC, datetime

from cortex.contracts.entities import SourceChunk, SourceFile, SourceObject
from cortex.contracts.enums import SourceChunkStatus
from cortex.ingestion.payloads import sha256_digest

from .config import ChunkingConfig


def stable_chunk_id(
    workspace_id: str,
    source_object_id: str,
    source_file_id: str | None,
    chunk_type: str,
    chunk_index: int,
    created_from_hash: str | None,
    chunking_version: str,
) -> str:
    parts = "|".join(
        [
            workspace_id,
            source_object_id,
            source_file_id or "",
            chunk_type,
            str(chunk_index),
            created_from_hash or "",
            chunking_version,
        ]
    )
    return f"chunk_{sha256_digest(parts.encode()).removeprefix('sha256:')[:24]}"


class SourceAwareChunker:
    def __init__(self, config: ChunkingConfig) -> None:
        self.config = config

    def chunks_for_source_object(
        self, source_object: SourceObject
    ) -> list[SourceChunk]:
        if source_object.object_type == "slack_thread":
            return self._chunks_for_slack_thread(source_object)

        title = source_object.title or source_object.external_object_id
        source_kind = source_object.metadata_json.get(
            "source_kind", source_object.object_type
        )
        text = (
            f"{title}\n"
            f"Source type: {source_kind}\n"
            f"Object: {source_object.external_object_key}"
        )
        return [
            self._chunk(
                source_object=source_object,
                source_file=None,
                chunk_type=f"{source_object.object_type}_overview",
                chunk_index=0,
                text=text,
                created_from_hash=source_object.content_hash,
            )
        ]

    def _chunks_for_slack_thread(
        self, source_object: SourceObject
    ) -> list[SourceChunk]:
        if not source_object.content_text:
            return []
        return [
            self._chunk(
                source_object=source_object,
                source_file=None,
                chunk_type="slack_message",
                chunk_index=0,
                text=source_object.content_text,
                created_from_hash=source_object.content_hash,
                citation_label="Slack thread",
                metadata_json={
                    "object_type": source_object.object_type,
                    "source_kind": source_object.metadata_json.get("source_kind"),
                    "channel_id_hash": source_object.metadata_json.get(
                        "channel_id_hash"
                    ),
                    "message_ts": source_object.metadata_json.get("message_ts"),
                    "thread_ts": source_object.metadata_json.get("thread_ts"),
                    "has_files": source_object.metadata_json.get("has_files"),
                    "has_links": source_object.metadata_json.get("has_links"),
                },
            )
        ]

    def chunks_for_source_file(
        self, source_object: SourceObject, source_file: SourceFile
    ) -> list[SourceChunk]:
        chunks = [
            self._chunk(
                source_object=source_object,
                source_file=source_file,
                chunk_type="file_metadata",
                chunk_index=0,
                text=(
                    f"{source_object.title or source_object.external_object_id}\n"
                    f"Content type: {source_file.content_type or 'unknown'}"
                ),
                created_from_hash=source_file.content_hash,
            )
        ]
        if source_file.ocr_text:
            chunks.append(
                self._chunk(
                    source_object=source_object,
                    source_file=source_file,
                    chunk_type="ocr_text",
                    chunk_index=1,
                    text=source_file.ocr_text,
                    created_from_hash=source_file.ocr_text_hash,
                )
            )
        return chunks

    def _chunk(
        self,
        *,
        source_object: SourceObject,
        source_file: SourceFile | None,
        chunk_type: str,
        chunk_index: int,
        text: str,
        created_from_hash: str | None,
        citation_label: str | None = None,
        metadata_json: dict[str, object] | None = None,
    ) -> SourceChunk:
        now = datetime.now(UTC)
        return SourceChunk(
            id=stable_chunk_id(
                source_object.workspace_id,
                source_object.id,
                source_file.id if source_file else None,
                chunk_type,
                chunk_index,
                created_from_hash,
                self.config.version,
            ),
            workspace_id=source_object.workspace_id,
            source_object_id=source_object.id,
            source_file_id=source_file.id if source_file else None,
            chunk_type=chunk_type,
            chunk_index=chunk_index,
            text=text,
            text_hash=sha256_digest(text.encode()),
            token_count=len(text.split()),
            chunking_version=self.config.version,
            citation_label=citation_label
            or source_object.title
            or source_object.external_object_id,
            citation_url=source_object.canonical_url,
            metadata_json=metadata_json or {"object_type": source_object.object_type},
            status=SourceChunkStatus.ACTIVE,
            created_from_hash=created_from_hash,
            created_at=now,
            updated_at=now,
        )
