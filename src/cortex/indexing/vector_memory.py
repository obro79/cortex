from __future__ import annotations

from typing import Any


class InMemoryVectorIndex:
    def __init__(self) -> None:
        self.collections: dict[str, int] = {}
        self.points: dict[str, dict[str, tuple[list[float], dict[str, Any]]]] = {}

    async def ensure_collection(self, name: str, dimensions: int) -> None:
        self.collections[name] = dimensions
        self.points.setdefault(name, {})

    async def upsert(
        self,
        collection: str,
        point_id: str,
        vector: list[float],
        payload: dict[str, Any],
    ) -> None:
        if collection not in self.collections:
            raise ValueError(f"collection does not exist: {collection}")
        forbidden = {
            "text",
            "chunk_text",
            "source_text",
            "ocr_text",
            "embedding",
            "vector",
        }
        if forbidden.intersection(payload):
            raise ValueError("vector payload contains content-bearing metadata")
        self.points[collection][point_id] = (vector, payload)

    async def delete(self, collection: str, point_id: str) -> None:
        self.points.get(collection, {}).pop(point_id, None)

    async def search(
        self, collection: str, vector: list[float], limit: int
    ) -> list[dict[str, Any]]:
        del vector
        return [
            {"id": point_id, "payload": payload}
            for point_id, (_stored_vector, payload) in list(
                self.points.get(collection, {}).items()
            )[:limit]
        ]

    async def health(self) -> bool:
        return True
