from typing import Protocol


class RateLimiter(Protocol):
    async def check(self, key: str, limit: int, window_seconds: int) -> bool: ...

    async def record(self, key: str, window_seconds: int) -> None: ...
