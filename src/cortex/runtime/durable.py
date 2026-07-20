"""SQL/Qdrant retrieval composition for the durable HTTP runtime."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from cortex.chunking.config import RetrievalConfig, load_retrieval_config
from cortex.chunking.repositories import SqlAlchemySourceChunkRepository
from cortex.config import Settings
from cortex.contracts.entities import EvidencePack, RetrievalRequest
from cortex.embeddings.profile import EmbeddingIndexProfile
from cortex.events.in_memory import InMemoryEventBus
from cortex.indexing.qdrant import QdrantVectorIndex
from cortex.permissions import ProviderAclPrincipal
from cortex.permissions.service import PermissionService
from cortex.retrieval.publishers import EvidencePackPublisher
from cortex.retrieval.repositories import (
    SqlAlchemyEvidencePackRepository,
    SqlAlchemyRetrievalRequestRepository,
)
from cortex.retrieval.service import RetrievalService, RetrievalServiceResponse
from cortex.utils.asyncio import maybe_await

PermissionServiceFactory = Callable[
    [AsyncSession, str], PermissionService | Awaitable[PermissionService]
]


class DurableContextRetrieval:
    """Construct retrieval dependencies per operation, never retaining a session.

    SQL remains canonical for chunks and evidence. Qdrant is only the derived
    vector candidate source; failures are reported by ``RetrievalService`` as a
    partial lexical result when FTS yields candidates.
    """

    def __init__(
        self,
        *,
        session_factory: async_sessionmaker[AsyncSession],
        settings: Settings,
        config: RetrievalConfig | None = None,
        vector_index: QdrantVectorIndex | None = None,
        permission_service_factory: PermissionServiceFactory | None = None,
    ) -> None:
        if not settings.qdrant_url:
            raise ValueError("QDRANT_URL is required for durable context retrieval")
        self.session_factory = session_factory
        self.settings = settings
        self.config = config or load_retrieval_config()
        self.embedding_profile = EmbeddingIndexProfile.from_settings(
            settings, config=self.config
        )
        self.vector_index = vector_index or QdrantVectorIndex.from_settings(settings)
        # SQL scopes and provider ACL snapshots must be injected by the
        # composition root.  Until their durable repositories are available,
        # task retrieval fails closed instead of treating all canonical chunks
        # as readable.
        self.permission_service_factory = permission_service_factory
        self.vector_collection = self.embedding_profile.collection

    async def _service(
        self, session: AsyncSession, *, workspace_id: str
    ) -> RetrievalService:
        if self.permission_service_factory is None:
            raise RuntimeError("durable_permission_service_unavailable")
        permission_service = await maybe_await(
            self.permission_service_factory(session, workspace_id)
        )
        return RetrievalService(
            config=self.config,
            source_chunks=SqlAlchemySourceChunkRepository(session),
            vector_index=self.vector_index,
            request_repository=SqlAlchemyRetrievalRequestRepository(session),
            evidence_repository=SqlAlchemyEvidencePackRepository(session),
            # Retrieval persistence must not depend on a best-effort event bus.
            publisher=EvidencePackPublisher(InMemoryEventBus()),
            vector_collection=self.vector_collection,
            query_embedder=self.embedding_profile.query_embedder(),
            permission_service=permission_service,
        )

    async def retrieve_context(
        self,
        *,
        workspace_id: str,
        query: str,
        source_allowlist: list[str] | None = None,
        provider_filters: list[str] | None = None,
        caller_principals: list[ProviderAclPrincipal] | None = None,
    ) -> RetrievalServiceResponse:
        async with self.session_factory() as session:
            try:
                service = await self._service(session, workspace_id=workspace_id)
                result = await service.retrieve_context(
                    workspace_id=workspace_id,
                    query=query,
                    source_allowlist=source_allowlist,
                    provider_filters=provider_filters,
                    caller_principals=caller_principals,
                )
                await session.commit()
                return result
            except Exception:
                await session.rollback()
                raise

    async def get_related_work(self, **kwargs: object) -> RetrievalServiceResponse:
        return await self.retrieve_context(**kwargs)  # type: ignore[arg-type]

    async def read_evidence_pack(self, evidence_pack_id: str) -> EvidencePack:
        async with self.session_factory() as session:
            return await SqlAlchemyEvidencePackRepository(session).get_by_id(
                evidence_pack_id
            )

    async def read_retrieval_request(
        self, retrieval_request_id: str
    ) -> RetrievalRequest:
        async with self.session_factory() as session:
            return await SqlAlchemyRetrievalRequestRepository(session).get_by_id(
                retrieval_request_id
            )
