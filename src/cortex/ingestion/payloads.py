from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, Protocol


@dataclass(frozen=True)
class StoredPayload:
    payload_ref: str
    payload_hash: str
    payload_size_bytes: int


class PayloadStore(Protocol):
    def describe_json(self, payload: Any) -> StoredPayload: ...

    def put_json(self, payload: Any) -> StoredPayload: ...

    def get(self, payload_ref: str) -> bytes: ...


def canonical_json_bytes(payload: Any) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def sha256_digest(content: bytes) -> str:
    return f"sha256:{sha256(content).hexdigest()}"


class InMemoryPayloadStore:
    def __init__(self) -> None:
        self._payloads: dict[str, bytes] = {}
        self.write_count = 0

    def describe_json(self, payload: Any) -> StoredPayload:
        return self.describe_bytes(canonical_json_bytes(payload))

    def put_json(self, payload: Any) -> StoredPayload:
        return self.put_bytes(canonical_json_bytes(payload))

    def describe_bytes(self, content: bytes) -> StoredPayload:
        payload_hash = sha256_digest(content)
        return StoredPayload(
            payload_ref=f"memory://payloads/{payload_hash.removeprefix('sha256:')}",
            payload_hash=payload_hash,
            payload_size_bytes=len(content),
        )

    def put_bytes(self, content: bytes) -> StoredPayload:
        stored = self.describe_bytes(content)
        if stored.payload_ref not in self._payloads:
            self._payloads[stored.payload_ref] = content
            self.write_count += 1
        return stored

    def get(self, payload_ref: str) -> bytes:
        try:
            return self._payloads[payload_ref]
        except KeyError as error:
            raise PayloadNotFoundError(payload_ref) from error


class FilePayloadStore:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def describe_json(self, payload: Any) -> StoredPayload:
        return self.describe_bytes(canonical_json_bytes(payload))

    def put_json(self, payload: Any) -> StoredPayload:
        return self.put_bytes(canonical_json_bytes(payload))

    def describe_bytes(self, content: bytes) -> StoredPayload:
        payload_hash = sha256_digest(content)
        digest = payload_hash.removeprefix("sha256:")
        return StoredPayload(
            payload_ref=f"file://payloads/{digest}",
            payload_hash=payload_hash,
            payload_size_bytes=len(content),
        )

    def put_bytes(self, content: bytes) -> StoredPayload:
        stored = self.describe_bytes(content)
        path = self._path_for_ref(stored.payload_ref)
        if not path.exists():
            path.write_bytes(content)
        return stored

    def get(self, payload_ref: str) -> bytes:
        path = self._path_for_ref(payload_ref)
        if not path.exists():
            raise PayloadNotFoundError(payload_ref)
        return path.read_bytes()

    def _path_for_ref(self, payload_ref: str) -> Path:
        prefix = "file://payloads/"
        if not payload_ref.startswith(prefix):
            raise PayloadNotFoundError(payload_ref)
        digest = payload_ref.removeprefix(prefix)
        if "/" in digest or not digest:
            raise PayloadNotFoundError(payload_ref)
        return self.root / digest


class PayloadNotFoundError(Exception):
    def __init__(self, payload_ref: str) -> None:
        super().__init__(f"payload not found: {payload_ref}")
        self.payload_ref = payload_ref
