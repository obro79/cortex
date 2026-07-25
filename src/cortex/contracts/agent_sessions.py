"""Contracts for explicitly exported, structured agent checkpoints.

These contracts deliberately model a caller-supplied export, not a native agent
session.  Cortex does not discover, inspect, resume, or control private Codex,
Claude Code, Cursor, or other agent sessions.
"""

from __future__ import annotations

import re
from enum import StrEnum
from typing import Any, Literal

from pydantic import Field, field_validator, model_validator

from cortex.contracts.entities import EntityModel
from cortex.ingestion.payloads import canonical_json_bytes, sha256_digest

EXPORT_MARKER = "agent_checkpoint_export_v1"
MAX_SUMMARY_LENGTH = 4_000
MAX_ITEMS_PER_SECTION = 100

_SECRET_PATTERNS = (
    re.compile(r"\b(?:sk|rk|pk)_[A-Za-z0-9_-]{16,}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bxox(?:a|b|p|r|s)-[A-Za-z0-9-]{10,}\b"),
    re.compile(r"\bxapp-[A-Za-z0-9-]{10,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{16,}\b", re.IGNORECASE),
)
_SENSITIVE_PATH_PARTS = (
    ".env",
    ".pem",
    ".key",
    "credential",
    "secret",
    "token",
    "id_rsa",
    "private",
)
_FORBIDDEN_EXPORT_KEYS = frozenset(
    {
        "transcript",
        "full_transcript",
        "messages",
        "native_session_id",
        "session_id",
        "control_handle",
        "resume_handle",
        "fork_handle",
    }
)


class AgentCheckpointProvider(StrEnum):
    CODEX = "codex"
    CLAUDE_CODE = "claude_code"
    CURSOR = "cursor"
    OTHER = "other"


class AgentCheckpointVisibility(StrEnum):
    PRIVATE = "private"
    WORKSPACE = "workspace"


class AgentTaskState(StrEnum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETE = "complete"


class CheckpointDecision(EntityModel):
    summary: str = Field(min_length=1, max_length=MAX_SUMMARY_LENGTH)
    rationale: str | None = Field(default=None, max_length=MAX_SUMMARY_LENGTH)


class CheckpointFileSummary(EntityModel):
    path: str = Field(min_length=1, max_length=1_024)
    summary: str = Field(min_length=1, max_length=MAX_SUMMARY_LENGTH)
    sensitive_path: bool = False

    @property
    def is_sensitive(self) -> bool:
        lowered = self.path.lower()
        return self.sensitive_path or any(
            part in lowered for part in _SENSITIVE_PATH_PARTS
        )

    @property
    def path_hash(self) -> str:
        return sha256_digest(self.path.encode())


class CheckpointCommandSummary(EntityModel):
    summary: str = Field(min_length=1, max_length=MAX_SUMMARY_LENGTH)
    outcome: str | None = Field(default=None, max_length=MAX_SUMMARY_LENGTH)


class CheckpointTestSummary(EntityModel):
    summary: str = Field(min_length=1, max_length=MAX_SUMMARY_LENGTH)
    outcome: str | None = Field(default=None, max_length=MAX_SUMMARY_LENGTH)


class CheckpointEvidenceReference(EntityModel):
    label: str = Field(min_length=1, max_length=512)
    reference: str = Field(min_length=1, max_length=2_048)


class AgentCheckpointExport(EntityModel):
    """A structured, opt-in checkpoint export with no transcript or control data."""

    export_marker: Literal["agent_checkpoint_export_v1"]
    export_enabled: Literal[True]
    checkpoint_id: str = Field(min_length=1, max_length=256)
    provider: AgentCheckpointProvider
    local_session_ref: str = Field(min_length=16, max_length=512)
    task_state: AgentTaskState
    task_summary: str = Field(min_length=1, max_length=MAX_SUMMARY_LENGTH)
    decisions: tuple[CheckpointDecision, ...] = Field(
        default=(), max_length=MAX_ITEMS_PER_SECTION
    )
    files: tuple[CheckpointFileSummary, ...] = Field(
        default=(), max_length=MAX_ITEMS_PER_SECTION
    )
    commands: tuple[CheckpointCommandSummary, ...] = Field(
        default=(), max_length=MAX_ITEMS_PER_SECTION
    )
    tests: tuple[CheckpointTestSummary, ...] = Field(
        default=(), max_length=MAX_ITEMS_PER_SECTION
    )
    next_actions: tuple[str, ...] = Field(default=(), max_length=MAX_ITEMS_PER_SECTION)
    evidence_references: tuple[CheckpointEvidenceReference, ...] = Field(
        default=(), max_length=MAX_ITEMS_PER_SECTION
    )
    visibility: AgentCheckpointVisibility = AgentCheckpointVisibility.PRIVATE
    content_hash: str = Field(pattern=r"^sha256:[a-f0-9]{64}$")

    @field_validator("checkpoint_id", "local_session_ref")
    @classmethod
    def require_trimmed_identifier(cls, value: str) -> str:
        if value != value.strip():
            raise ValueError("identifier values must be trimmed")
        return value

    @field_validator("next_actions")
    @classmethod
    def validate_actions(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        for action in value:
            if not action.strip() or len(action) > MAX_SUMMARY_LENGTH:
                raise ValueError("next actions must be non-empty bounded summaries")
        return value

    @model_validator(mode="after")
    def validate_safe_export(self) -> AgentCheckpointExport:
        payload = self.content_payload()
        _assert_no_forbidden_keys(payload)
        _assert_no_secrets(payload)
        if self.content_hash != sha256_digest(canonical_json_bytes(payload)):
            raise ValueError(
                "content_hash does not match structured checkpoint content"
            )
        return self

    def content_payload(self) -> dict[str, Any]:
        """Return hashable structured content without local-only reference data."""
        return {
            "checkpoint_id": self.checkpoint_id,
            "provider": str(self.provider),
            "task_state": str(self.task_state),
            "task_summary": self.task_summary,
            "decisions": [decision.model_dump() for decision in self.decisions],
            "files": [file.model_dump() for file in self.files],
            "commands": [command.model_dump() for command in self.commands],
            "tests": [test.model_dump() for test in self.tests],
            "next_actions": list(self.next_actions),
            "evidence_references": [
                evidence.model_dump() for evidence in self.evidence_references
            ],
            "visibility": str(self.visibility),
        }

    def to_payload(self) -> dict[str, Any]:
        """Build the only payload accepted by the agent-session normalizer."""
        return {
            "export_marker": self.export_marker,
            "export_enabled": self.export_enabled,
            "local_session_ref_hash": sha256_digest(self.local_session_ref.encode()),
            "content_hash": self.content_hash,
            "checkpoint": self.content_payload(),
        }


class AgentCheckpointDeletionPlan(EntityModel):
    """Plan deletion/revocation without controlling an agent."""

    checkpoint_id: str = Field(min_length=1, max_length=256)
    local_session_ref_hash: str = Field(pattern=r"^sha256:[a-f0-9]{64}$")
    action: Literal["delete_export", "revoke_export"]

    @property
    def external_object_key(self) -> str:
        return f"agent_session:checkpoint:{self.checkpoint_id}"


def content_hash_for_checkpoint(content: dict[str, Any]) -> str:
    """Helper for exporters constructing a valid explicit export."""
    return sha256_digest(canonical_json_bytes(content))


def _assert_no_forbidden_keys(value: Any, *, path: str = "checkpoint") -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if key.lower() in _FORBIDDEN_EXPORT_KEYS:
                raise ValueError(f"{path}.{key} is not allowed in checkpoint exports")
            _assert_no_forbidden_keys(item, path=f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _assert_no_forbidden_keys(item, path=f"{path}[{index}]")


def _assert_no_secrets(value: Any) -> None:
    if isinstance(value, str):
        if any(pattern.search(value) for pattern in _SECRET_PATTERNS):
            raise ValueError("checkpoint exports must redact secrets before submission")
    elif isinstance(value, dict):
        for item in value.values():
            _assert_no_secrets(item)
    elif isinstance(value, list):
        for item in value:
            _assert_no_secrets(item)
