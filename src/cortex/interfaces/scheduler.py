from datetime import datetime
from typing import Any, Protocol


class Scheduler(Protocol):
    async def enqueue(self, job_name: str, payload: dict[str, Any]) -> str: ...

    async def schedule(
        self, job_name: str, payload: dict[str, Any], run_at: datetime
    ) -> str: ...
