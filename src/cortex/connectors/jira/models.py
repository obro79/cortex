"""Planned Jira snapshot models; this module does not call Jira APIs."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

MAX_CURSOR_LENGTH = 2048


def _text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    rendered = value.strip()
    return rendered or None


def _mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


@dataclass(frozen=True)
class JiraSnapshotPageInput:
    """A bounded, cursor-based request shape for an externally supplied snapshot."""

    project_ids: tuple[str, ...] = ()
    cursor: str | None = None
    page_size: int = 100

    def __post_init__(self) -> None:
        if any(not isinstance(project_id, str) for project_id in self.project_ids):
            raise ValueError("jira project_ids must be non-empty and unique")
        project_ids = tuple(
            dict.fromkeys(
                project_id.strip()
                for project_id in self.project_ids
                if project_id.strip()
            )
        )
        if len(project_ids) != len(self.project_ids):
            raise ValueError("jira project_ids must be non-empty and unique")
        if not 1 <= self.page_size <= 100:
            raise ValueError("jira page_size must be between 1 and 100")
        if self.cursor is not None and (
            not isinstance(self.cursor, str)
            or not self.cursor.strip()
            or len(self.cursor) > MAX_CURSOR_LENGTH
        ):
            raise ValueError("jira cursor must be non-empty when supplied")


@dataclass(frozen=True)
class JiraIssueSnapshot:
    issue_id: str
    issue_key: str
    title: str
    description: str | None
    url: str | None
    project_id: str | None
    status: str | None
    updated_at: str | None

    @classmethod
    def from_provider_payload(cls, payload: Mapping[str, object]) -> JiraIssueSnapshot:
        fields = _mapping(payload.get("fields"))
        issue_id = _text(payload.get("id"))
        issue_key = _text(payload.get("key"))
        title = _text(fields.get("summary"))
        if not issue_id or not issue_key or not title:
            raise ValueError("jira snapshot requires id, key, and fields.summary")
        project = _mapping(fields.get("project"))
        status = _mapping(fields.get("status"))
        return cls(
            issue_id=issue_id,
            issue_key=issue_key,
            title=title,
            description=_text(fields.get("description")),
            url=_text(payload.get("self")),
            project_id=_text(project.get("id")),
            status=_text(status.get("name")),
            updated_at=_text(fields.get("updated")),
        )

    def to_payload(self) -> dict[str, str | None]:
        return {
            "id": self.issue_id,
            "key": self.issue_key,
            "title": self.title,
            "description": self.description,
            "url": self.url,
            "project_id": self.project_id,
            "status": self.status,
            "updated_at": self.updated_at,
        }


@dataclass(frozen=True)
class JiraSnapshotPage:
    input: JiraSnapshotPageInput
    issues: tuple[JiraIssueSnapshot, ...]
    next_cursor: str | None = None

    def __post_init__(self) -> None:
        if len(self.issues) > self.input.page_size:
            raise ValueError("jira snapshot page exceeds requested page_size")
        if len({issue.issue_id for issue in self.issues}) != len(self.issues):
            raise ValueError("jira snapshot page contains duplicate issue ids")
        if self.next_cursor is not None and (
            not isinstance(self.next_cursor, str)
            or not self.next_cursor.strip()
            or len(self.next_cursor) > MAX_CURSOR_LENGTH
        ):
            raise ValueError("jira next_cursor must be non-empty when supplied")
        if self.next_cursor is not None and self.next_cursor == self.input.cursor:
            raise ValueError("jira next_cursor must advance the cursor")

    @property
    def next_page_input(self) -> JiraSnapshotPageInput | None:
        if self.next_cursor is None:
            return None
        return JiraSnapshotPageInput(
            project_ids=self.input.project_ids,
            cursor=self.next_cursor,
            page_size=self.input.page_size,
        )
