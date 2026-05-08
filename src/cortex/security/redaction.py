from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

REDACTED = "[REDACTED]"

SENSITIVE_KEY_PARTS = (
    "authorization",
    "cookie",
    "embedding",
    "file",
    "oauth",
    "password",
    "payload",
    "private_url",
    "query",
    "raw",
    "secret",
    "source_text",
    "text",
    "token",
    "url",
    "vector",
)

FORBIDDEN_CONTENT_KEYS = frozenset(
    {
        "raw_payload",
        "source_text",
        "chunk_text",
        "content_text",
        "message_text",
        "ocr_text",
        "embedding",
        "vector",
        "oauth_token",
        "access_token",
        "refresh_token",
        "authorization",
        "secret",
        "private_url",
        "url_private",
        "url_private_download",
    }
)


@dataclass(frozen=True)
class UnsafePayloadFinding:
    path: str
    key: str


def is_sensitive_key(key: str) -> bool:
    lowered = key.lower()
    return any(part in lowered for part in SENSITIVE_KEY_PARTS)


def redact_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return redact_mapping(value)
    if isinstance(value, list):
        return [redact_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_value(item) for item in value)
    return value


def redact_mapping(value: Mapping[str, Any]) -> dict[str, Any]:
    redacted: dict[str, Any] = {}
    for key, item in value.items():
        if is_sensitive_key(key):
            redacted[key] = REDACTED if item else item
        else:
            redacted[key] = redact_value(item)
    return redacted


def unsafe_payload_findings(
    value: Any, *, path: str = "payload"
) -> list[UnsafePayloadFinding]:
    findings: list[UnsafePayloadFinding] = []
    if isinstance(value, Mapping):
        for key, item in value.items():
            key_text = str(key)
            next_path = f"{path}.{key_text}"
            if key_text.lower() in FORBIDDEN_CONTENT_KEYS:
                findings.append(UnsafePayloadFinding(path=next_path, key=key_text))
            findings.extend(unsafe_payload_findings(item, path=next_path))
    elif isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        for index, item in enumerate(value):
            findings.extend(unsafe_payload_findings(item, path=f"{path}[{index}]"))
    return findings


def assert_payload_safe(value: Mapping[str, Any]) -> None:
    findings = unsafe_payload_findings(value)
    if findings:
        keys = ", ".join(sorted({finding.key for finding in findings}))
        msg = f"payload contains forbidden content-bearing keys: {keys}"
        raise ValueError(msg)
