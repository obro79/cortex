from typing import Protocol


class Worker(Protocol):
    async def start(self) -> None: ...

    async def stop(self) -> None: ...
