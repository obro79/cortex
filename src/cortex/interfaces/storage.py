from typing import Protocol


class ObjectStorage(Protocol):
    async def put(
        self, key: str, content: bytes, content_type: str | None = None
    ) -> str: ...

    async def get(self, ref: str) -> bytes: ...

    async def delete(self, ref: str) -> None: ...
