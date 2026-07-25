from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from cortex.config import Settings
from cortex.lifecycle import (
    LifecycleQueueRunResult,
    LifecycleQueueWorker,
    LifecycleService,
    SqlAlchemyLifecycleRepository,
)
from cortex.lifecycle.runtime import (
    create_sql_deletion_executor,
    create_sql_export_executor,
)


async def process_lifecycle_queue_once(
    *,
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
    worker_id: str,
) -> LifecycleQueueRunResult:
    async with session_factory() as session:
        try:
            repository = SqlAlchemyLifecycleRepository(session)
            service = LifecycleService(repository)
            worker = LifecycleQueueWorker(
                service=service,
                deletion_executor=create_sql_deletion_executor(
                    session=session,
                    settings=settings,
                ),
                export_executor=create_sql_export_executor(
                    session=session,
                    settings=settings,
                ),
                worker_id=worker_id,
            )
            result = await worker.process_once()
            await session.commit()
            return result
        except Exception:
            await session.rollback()
            raise
