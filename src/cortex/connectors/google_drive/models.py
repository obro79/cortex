"""Planned Google Drive snapshot models; this module does not call Google APIs."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass


def _text(value: object) -> str | None:
    if value is None:
        return None
    rendered = str(value).strip()
    return rendered or None


@dataclass(frozen=True)
class GoogleDriveSnapshotPageInput:
    """A bounded, cursor-based request shape for an externally supplied snapshot."""

    folder_id: str | None = None
    cursor: str | None = None
    page_size: int = 100

    def __post_init__(self) -> None:
        if self.folder_id is not None and not self.folder_id.strip():
            raise ValueError("google drive folder_id must be non-empty when supplied")
        if self.cursor is not None and not self.cursor.strip():
            raise ValueError("google drive cursor must be non-empty when supplied")
        if not 1 <= self.page_size <= 1000:
            raise ValueError("google drive page_size must be between 1 and 1000")


@dataclass(frozen=True)
class GoogleDriveFileSnapshot:
    file_id: str
    name: str
    mime_type: str
    description: str | None
    web_url: str | None
    modified_at: str | None
    parent_ids: tuple[str, ...]
    trashed: bool

    @classmethod
    def from_provider_payload(
        cls, payload: Mapping[str, object]
    ) -> GoogleDriveFileSnapshot:
        file_id = _text(payload.get("id"))
        name = _text(payload.get("name"))
        mime_type = _text(payload.get("mimeType"))
        if not file_id or not name or not mime_type:
            raise ValueError("google drive snapshot requires id, name, and mimeType")
        raw_parents = payload.get("parents")
        parent_ids = (
            tuple(str(parent).strip() for parent in raw_parents if str(parent).strip())
            if isinstance(raw_parents, list)
            else ()
        )
        return cls(
            file_id=file_id,
            name=name,
            mime_type=mime_type,
            description=_text(payload.get("description")),
            web_url=_text(payload.get("webViewLink")),
            modified_at=_text(payload.get("modifiedTime")),
            parent_ids=parent_ids,
            trashed=payload.get("trashed") is True,
        )

    def to_payload(self) -> dict[str, object]:
        return {
            "id": self.file_id,
            "name": self.name,
            "mime_type": self.mime_type,
            "description": self.description,
            "web_url": self.web_url,
            "modified_at": self.modified_at,
            "parent_ids": list(self.parent_ids),
            "trashed": self.trashed,
        }


@dataclass(frozen=True)
class GoogleDriveSnapshotPage:
    input: GoogleDriveSnapshotPageInput
    files: tuple[GoogleDriveFileSnapshot, ...]
    next_cursor: str | None = None

    def __post_init__(self) -> None:
        if self.next_cursor is not None and not self.next_cursor.strip():
            raise ValueError("google drive next_cursor must be non-empty when supplied")

    @property
    def next_page_input(self) -> GoogleDriveSnapshotPageInput | None:
        if self.next_cursor is None:
            return None
        return GoogleDriveSnapshotPageInput(
            folder_id=self.input.folder_id,
            cursor=self.next_cursor,
            page_size=self.input.page_size,
        )
