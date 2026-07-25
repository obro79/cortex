"""Qdrant implementation of the rebuildable, content-free vector index."""

from __future__ import annotations

import math
import re
import uuid
from collections.abc import Mapping, Sequence
from typing import Any

from qdrant_client import AsyncQdrantClient, models

from cortex.config import Settings
from cortex.interfaces.vector_index import VectorMetadataFilter

_POINT_NAMESPACE = uuid.UUID("dfe2b83e-7b79-4d30-b300-8c6e7345ee68")
_COLLECTION_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,254}$")
_LOGICAL_POINT_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_FORBIDDEN_PAYLOAD_KEY_PARTS = frozenset(
    {
        "bytes",
        "content",
        "embedding",
        "ocr",
        "payload",
        "raw",
        "secret",
        "snippet",
        "text",
        "token",
        "uri",
        "url",
        "vector",
    }
)
_ALLOWED_PAYLOAD_KEYS = frozenset(
    {
        "acl_revision",
        "chunk_type",
        "chunking_version",
        "content_hash",
        "embedding_id",
        "embedding_model",
        "embedding_version",
        "index_version",
        "provider",
        "scope_revision",
        "source_chunk_id",
        "source_file_id",
        "source_object_id",
        "source_allowlist_eligible",
        "source_scope",
        "source_type",
        "status",
        "workspace_id",
    }
)
_INTERNAL_POINT_ID_KEY = "_cortex_point_id"


class QdrantVectorIndex:
    """Async adapter for a Qdrant collection shared by Cortex workspaces.

    The application is responsible for deriving a stable logical point ID from
    the canonical embedding record. This adapter maps it to Qdrant's UUID point
    format deterministically, so retries and restarts overwrite the same point.
    """

    def __init__(self, client: Any) -> None:
        self._client = client

    @classmethod
    def from_settings(cls, settings: Settings) -> QdrantVectorIndex:
        if not settings.qdrant_url:
            raise ValueError("QDRANT_URL is required to construct QdrantVectorIndex")
        return cls(
            AsyncQdrantClient(
                url=settings.qdrant_url,
                api_key=settings.qdrant_api_key or None,
            )
        )

    async def ensure_collection(self, name: str, dimensions: int) -> None:
        validate_collection_name(name)
        if dimensions <= 0:
            raise ValueError("Qdrant collection dimensions must be positive")

        if await self._client.collection_exists(collection_name=name):
            await self._validate_collection_schema(name, dimensions)
            return

        try:
            await self._client.create_collection(
                collection_name=name,
                vectors_config=models.VectorParams(
                    size=dimensions,
                    distance=models.Distance.COSINE,
                ),
            )
        except Exception:
            # A concurrent bootstrap can create the collection after the first
            # existence check. Re-read it before treating the failure as fatal.
            if not await self._client.collection_exists(collection_name=name):
                raise
        await self._validate_collection_schema(name, dimensions)

    async def upsert(
        self,
        collection: str,
        point_id: str,
        vector: list[float],
        payload: dict[str, Any],
    ) -> None:
        validate_collection_name(collection)
        validate_point_id(point_id)
        _validate_vector(vector)
        safe_payload = validate_payload(payload)
        safe_payload[_INTERNAL_POINT_ID_KEY] = point_id
        await self._client.upsert(
            collection_name=collection,
            points=[
                models.PointStruct(
                    id=qdrant_point_id(collection, point_id),
                    vector=vector,
                    payload=safe_payload,
                )
            ],
            wait=True,
        )

    async def delete(self, collection: str, point_id: str) -> None:
        validate_collection_name(collection)
        validate_point_id(point_id)
        await self._client.delete(
            collection_name=collection,
            points_selector=models.PointIdsList(
                points=[qdrant_point_id(collection, point_id)]
            ),
            wait=True,
        )

    async def search(
        self, collection: str, vector: list[float], limit: int
    ) -> list[dict[str, Any]]:
        return await self.search_filtered(collection, vector, filters=None, limit=limit)

    async def search_filtered(
        self,
        collection: str,
        vector: list[float],
        *,
        filters: VectorMetadataFilter | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        validate_collection_name(collection)
        _validate_vector(vector)
        if limit <= 0:
            return []
        query_filter = _build_filter(filters)
        response = await self._client.query_points(
            collection_name=collection,
            query=vector,
            query_filter=query_filter,
            limit=limit,
            with_payload=True,
            with_vectors=False,
        )
        return [_to_hit(result) for result in response.points]

    async def health(self) -> bool:
        try:
            await self._client.get_collections()
        except Exception:
            return False
        return True

    async def close(self) -> None:
        close = getattr(self._client, "close", None)
        if close is not None:
            result = close()
            if hasattr(result, "__await__"):
                await result

    async def _validate_collection_schema(
        self, collection: str, expected_dimensions: int
    ) -> None:
        info = await self._client.get_collection(collection_name=collection)
        actual_dimensions = _collection_dimensions(info)
        if actual_dimensions != expected_dimensions:
            raise ValueError(
                f"Qdrant collection {collection!r} has dimensions "
                f"{actual_dimensions}, expected {expected_dimensions}"
            )
        distance = _collection_distance(info)
        if distance is not models.Distance.COSINE:
            raise ValueError(
                f"Qdrant collection {collection!r} has distance {distance!s}, "
                "expected Cosine"
            )


def validate_collection_name(name: str) -> None:
    if not _COLLECTION_NAME.fullmatch(name):
        raise ValueError(
            "Qdrant collection name must be 1-255 characters of letters, "
            "numbers, '.', '_', or '-', beginning with a letter or number"
        )


def validate_point_id(point_id: str) -> None:
    if not _LOGICAL_POINT_ID.fullmatch(point_id):
        raise ValueError(
            "Qdrant point_id must be a compact identifier of up to 128 letters, "
            "numbers, '.', '_', ':', or '-'"
        )


def validate_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Allow only compact, filterable metadata in the derived index."""
    safe_payload: dict[str, Any] = {}
    for key, value in payload.items():
        if not isinstance(key, str) or not key:
            raise ValueError("Qdrant payload keys must be non-empty strings")
        key_parts = set(re.split(r"[^a-z0-9]+", key.lower()))
        if key_parts & _FORBIDDEN_PAYLOAD_KEY_PARTS:
            raise ValueError("Qdrant payload contains content-bearing metadata")
        if key not in _ALLOWED_PAYLOAD_KEYS:
            raise ValueError(f"Qdrant payload key {key!r} is not permitted")
        safe_payload[key] = _validate_payload_value(key, value)
    return safe_payload


def _validate_payload_value(
    key: str, value: Any
) -> str | int | float | bool | None | list[Any]:
    if value is None or isinstance(value, (bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"Qdrant payload {key!r} must be finite")
        return value
    if isinstance(value, str):
        if len(value) > 512:
            raise ValueError(f"Qdrant payload {key!r} is too large for metadata")
        return value
    if isinstance(value, list):
        if len(value) > 64:
            raise ValueError(f"Qdrant payload {key!r} contains too many values")
        return [_validate_payload_value(key, item) for item in value]
    raise ValueError(f"Qdrant payload {key!r} must contain only scalar metadata")


def _validate_vector(vector: Sequence[float]) -> None:
    if not vector:
        raise ValueError("Qdrant vector must not be empty")
    if not all(
        isinstance(value, (int, float)) and math.isfinite(value) for value in vector
    ):
        raise ValueError("Qdrant vector must contain only finite numbers")


def _build_filter(
    filters: VectorMetadataFilter | None,
) -> models.Filter | None:
    if not filters:
        return None
    conditions: list[Any] = []
    for key, value in filters.items():
        validate_payload({key: value})
        if isinstance(value, list):
            conditions.append(
                models.FieldCondition(key=key, match=models.MatchAny(any=value))
            )
            continue
        conditions.append(
            models.FieldCondition(key=key, match=models.MatchValue(value=value))
        )
    return models.Filter(must=conditions)


def qdrant_point_id(collection: str, point_id: str) -> str:
    """Return Qdrant's deterministic UUID for a Cortex logical point ID."""
    validate_collection_name(collection)
    validate_point_id(point_id)
    return str(uuid.uuid5(_POINT_NAMESPACE, f"{collection}:{point_id}"))


def _collection_dimensions(info: Any) -> int:
    vectors = info.config.params.vectors
    size = getattr(vectors, "size", None)
    if not isinstance(size, int):
        raise ValueError("Qdrant collection has an unsupported named-vector schema")
    return size


def _collection_distance(info: Any) -> models.Distance:
    vectors = info.config.params.vectors
    distance = getattr(vectors, "distance", None)
    try:
        return models.Distance(distance)
    except (TypeError, ValueError) as error:
        raise ValueError(
            "Qdrant collection has an unsupported distance metric"
        ) from error


def _to_hit(result: Any) -> dict[str, Any]:
    payload = dict(result.payload or {})
    point_id = str(payload.pop(_INTERNAL_POINT_ID_KEY, result.id))
    hit: dict[str, Any] = {"id": point_id, "payload": payload}
    score = getattr(result, "score", None)
    if isinstance(score, (int, float)):
        hit["score"] = float(score)
    return hit
