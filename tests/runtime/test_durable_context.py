from typing import cast

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from cortex.api.app import create_app
from cortex.config import Settings
from cortex.indexing.qdrant import QdrantVectorIndex
from cortex.runtime import CortexRuntime
from cortex.runtime.durable import DurableContextRetrieval


def test_durable_retrieval_uses_indexing_collection_name_convention() -> None:
    settings = Settings(
        cortex_env="test",
        qdrant_url="http://localhost:6333",
        qdrant_collection_prefix="cortex",
    )
    retrieval = DurableContextRetrieval(
        session_factory=cast(async_sessionmaker[AsyncSession], object()),
        settings=settings,
        vector_index=cast(QdrantVectorIndex, object()),
    )

    assert retrieval.vector_collection == settings.qdrant_collection_name(
        embedding_model="deterministic",
        embedding_version="gemini-1536-v1",
        dimensions=16,
    )


def test_sql_app_composes_durable_runtime_only_with_qdrant() -> None:
    app = create_app(
        Settings(
            cortex_state_backend="sql",
            database_url="postgresql+asyncpg://user:pass@localhost/cortex",
            qdrant_url="http://localhost:6333",
        )
    )

    assert isinstance(app.state.cortex_runtime, CortexRuntime)
    assert isinstance(app.state.cortex_runtime.retrieval, DurableContextRetrieval)


def test_durable_retrieval_requires_a_permission_service_factory() -> None:
    settings = Settings(cortex_env="test", qdrant_url="http://localhost:6333")
    retrieval = DurableContextRetrieval(
        session_factory=cast(async_sessionmaker[AsyncSession], object()),
        settings=settings,
        vector_index=cast(QdrantVectorIndex, object()),
    )

    with pytest.raises(RuntimeError, match="durable_permission_service_unavailable"):
        retrieval._service(cast(AsyncSession, object()))
