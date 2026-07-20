"""Fixture-supplied GitHub snapshot models; this module makes no API calls."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


def _text(value: object) -> str | None:
    if value is None:
        return None
    rendered = str(value).strip()
    return rendered or None


def _mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


@dataclass(frozen=True)
class GitHubSnapshotPageInput:
    """A bounded request shape for a supplied, offline GitHub snapshot page."""

    repository_ids: tuple[str, ...] = ()
    cursor: str | None = None
    page_size: int = 100

    def __post_init__(self) -> None:
        repository_ids = tuple(
            dict.fromkeys(
                repository_id.strip()
                for repository_id in self.repository_ids
                if repository_id.strip()
            )
        )
        if len(repository_ids) != len(self.repository_ids):
            raise ValueError("github repository_ids must be non-empty and unique")
        if not 1 <= self.page_size <= 100:
            raise ValueError("github page_size must be between 1 and 100")
        if self.cursor is not None and not self.cursor.strip():
            raise ValueError("github cursor must be non-empty when supplied")


@dataclass(frozen=True)
class GitHubSnapshotEvent:
    """One PR, issue, or commit supplied by a snapshot fixture or exporter."""

    repository_id: str
    repository_full_name: str | None
    object_kind: str
    object_id: str
    updated_at: str | None
    payload: dict[str, Any]

    @classmethod
    def from_provider_event(cls, event: Mapping[str, object]) -> GitHubSnapshotEvent:
        repository = _mapping(event.get("repository"))
        repository_id = _text(repository.get("id")) or _text(event.get("repository_id"))
        if not repository_id:
            raise ValueError("github snapshot requires repository.id")
        repository_full_name = _text(repository.get("full_name"))

        object_kind, object_payload = _object_from_event(event)
        object_id = _object_id(object_kind, object_payload)
        if not object_id:
            raise ValueError(
                f"github {object_kind} snapshot requires a stable identifier"
            )

        payload = {str(key): value for key, value in event.items()}
        return cls(
            repository_id=repository_id,
            repository_full_name=repository_full_name,
            object_kind=object_kind,
            object_id=object_id,
            updated_at=_updated_at(object_payload),
            payload=payload,
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "repository_id": self.repository_id,
            "repository_full_name": self.repository_full_name,
            "object_kind": self.object_kind,
            "object_id": self.object_id,
            "updated_at": self.updated_at,
            "event": self.payload,
        }


@dataclass(frozen=True)
class GitHubSnapshotPage:
    input: GitHubSnapshotPageInput
    events: tuple[GitHubSnapshotEvent, ...]
    next_cursor: str | None = None

    def __post_init__(self) -> None:
        if self.next_cursor is not None and not self.next_cursor.strip():
            raise ValueError("github next_cursor must be non-empty when supplied")

    @property
    def next_page_input(self) -> GitHubSnapshotPageInput | None:
        if self.next_cursor is None:
            return None
        return GitHubSnapshotPageInput(
            repository_ids=self.input.repository_ids,
            cursor=self.next_cursor,
            page_size=self.input.page_size,
        )


def _object_from_event(event: Mapping[str, object]) -> tuple[str, Mapping[str, object]]:
    for kind in ("pull_request", "issue", "commit"):
        payload = _mapping(event.get(kind))
        if payload:
            return kind, payload
    raise ValueError("github snapshot requires pull_request, issue, or commit")


def _object_id(kind: str, payload: Mapping[str, object]) -> str | None:
    if kind == "commit":
        return _text(payload.get("sha")) or _text(payload.get("id"))
    return _text(payload.get("id")) or _text(payload.get("number"))


def _updated_at(payload: Mapping[str, object]) -> str | None:
    return (
        _text(payload.get("updated_at"))
        or _text(payload.get("created_at"))
        or _text(payload.get("timestamp"))
    )
