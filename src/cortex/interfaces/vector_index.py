from collections.abc import Mapping
from typing import Any, Protocol

VectorMetadataScalar = str | int | bool
VectorMetadataList = list[str] | list[int]
VectorMetadataFilter = Mapping[
    str, VectorMetadataScalar | VectorMetadataList
]


class VectorIndex(Protocol):
    async def ensure_collection(self, name: str, dimensions: int) -> None: ...

    async def upsert(
        self,
        collection: str,
        point_id: str,
        vector: list[float],
        payload: dict[str, Any],
    ) -> None: ...

    async def delete(self, collection: str, point_id: str) -> None: ...

    async def search(
        self, collection: str, vector: list[float], limit: int
    ) -> list[dict[str, Any]]: ...

    async def health(self) -> bool: ...


class FilteredVectorIndex(VectorIndex, Protocol):
    """A VectorIndex that applies metadata equality filters server-side.

    Durable retrieval must pass its tenant and eligibility constraints here:
    ``workspace_id``, ``status``, current chunking/embedding/index versions,
    provider, and compact source-scope or ACL revision metadata. Payloads are
    intentionally metadata-only; retrieval hydrates content from Postgres.
    """

    async def search_filtered(
        self,
        collection: str,
        vector: list[float],
        *,
        filters: VectorMetadataFilter | None,
        limit: int,
    ) -> list[dict[str, Any]]: ...
