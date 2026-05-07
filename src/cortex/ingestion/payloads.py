from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from typing import Any


@dataclass(frozen=True)
class StoredPayload:
    payload_ref: str
    payload_hash: str
    payload_size_bytes: int


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


class PayloadNotFoundError(Exception):
    def __init__(self, payload_ref: str) -> None:
        super().__init__(f"payload not found: {payload_ref}")
        self.payload_ref = payload_ref
