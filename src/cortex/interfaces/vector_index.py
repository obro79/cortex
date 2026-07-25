from typing import Any, Protocol


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
