from typing import cast

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from cortex.api.app import create_app
from cortex.config import Settings
from cortex.indexing.qdrant import QdrantVectorIndex
from cortex.permissions.scopes import InMemoryPermissionScopeRepository
from cortex.permissions.service import PermissionService
from cortex.runtime import CortexRuntime
from cortex.runtime.durable import DurableContextRetrieval


def test_durable_retrieval_uses_shared_indexing_profile_collection() -> None:
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
        embedding_model="fixture-vector-v1",
        embedding_version="gemini-1536-v1",
        dimensions=16,
    )
    assert retrieval.vector_collection != "fixture-cortex-dev"


def test_sql_app_composes_durable_runtime_with_sql_scope_materializer() -> None:
    settings = Settings(
        cortex_state_backend="sql",
        database_url="postgresql+asyncpg://user:pass@localhost/cortex",
        qdrant_url="http://localhost:6333",
    )

    app = create_app(settings)
    assert isinstance(app.state.cortex_runtime, CortexRuntime)
    assert isinstance(app.state.cortex_runtime.retrieval, DurableContextRetrieval)

    injected = create_app(
        settings,
        durable_permission_service_factory=lambda _session, _workspace_id: (
            PermissionService(InMemoryPermissionScopeRepository())
        ),
    )

    assert isinstance(injected.state.cortex_runtime, CortexRuntime)
    assert isinstance(injected.state.cortex_runtime.retrieval, DurableContextRetrieval)


async def test_durable_retrieval_fails_closed_without_permission_factory() -> None:
    settings = Settings(cortex_env="test", qdrant_url="http://localhost:6333")
    retrieval = DurableContextRetrieval(
        session_factory=cast(async_sessionmaker[AsyncSession], object()),
        settings=settings,
        vector_index=cast(QdrantVectorIndex, object()),
    )

    with pytest.raises(RuntimeError, match="durable_permission_service_unavailable"):
        await retrieval._service(
            cast(AsyncSession, object()), workspace_id="workspace_1"
        )
