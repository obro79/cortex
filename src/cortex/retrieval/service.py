from __future__ import annotations

from dataclasses import dataclass

from cortex.chunking.config import RetrievalConfig
from cortex.chunking.repositories import InMemorySourceChunkRepository
from cortex.embeddings.deterministic import DeterministicEmbeddingProvider
from cortex.indexing.vector_memory import InMemoryVectorIndex

from .candidates import Candidate
from .evidence import EvidencePackBuilder
from .fts import FtsRetriever
from .permissions import PermissionFilter
from .publishers import EvidencePackPublisher
from .query import QueryPlanner
from .ranking import CandidateRanker
from .repositories import (
    InMemoryEvidencePackRepository,
    InMemoryRetrievalRequestRepository,
)
from .vector import VectorRetriever


@dataclass(frozen=True)
class RetrievalServiceResponse:
    ok: bool
    retrieval_request_id: str
    evidence_pack_id: str | None
    text: str
    evidence_pack: dict[str, object]
    status: str
    latency_ms: int | None


class RetrievalService:
    def __init__(
        self,
        *,
        config: RetrievalConfig,
        source_chunks: InMemorySourceChunkRepository,
        vector_index: InMemoryVectorIndex,
        request_repository: InMemoryRetrievalRequestRepository,
        evidence_repository: InMemoryEvidencePackRepository,
        publisher: EvidencePackPublisher,
    ) -> None:
        self.config = config
        self.source_chunks = source_chunks
        self.planner = QueryPlanner()
        self.fts = FtsRetriever(source_chunks)
        self.vector = VectorRetriever(
            vector_index=vector_index,
            source_chunks=source_chunks,
            embedder=DeterministicEmbeddingProvider(
                dimensions=16, version=config.embeddings.version
            ),
        )
        self.requests = request_repository
        self.evidence = evidence_repository
        self.publisher = publisher
        self.permissions = PermissionFilter()
        self.builder = EvidencePackBuilder()
        self.ranker = CandidateRanker(config.ranking)

    async def retrieve_context(
        self,
        *,
        workspace_id: str,
        query: str,
        source_allowlist: list[str] | None = None,
        provider_filters: list[str] | None = None,
    ) -> RetrievalServiceResponse:
        plan = self.planner.plan(
            query=query,
            provider_filters=provider_filters,
            source_allowlist=source_allowlist,
        )
        request = self.requests.create(
            workspace_id=workspace_id,
            query=query,
            filters_json={
                "provider_filters": plan.provider_filters,
                "source_allowlist": plan.source_allowlist,
            },
            source_allowlist_snapshot_hash=plan.source_allowlist_snapshot_hash,
        )
        candidates: list[Candidate] = []
        errors: dict[str, str] = {}
        try:
            candidates.extend(
                self.fts.retrieve(
                    workspace_id=workspace_id,
                    plan=plan,
                    chunking_version=self.config.chunking.version,
                    limit=int(self.config.candidate_retrieval["fts_candidate_limit"]),
                )
            )
        except Exception as error:
            errors["fts"] = type(error).__name__
        try:
            candidates.extend(
                await self.vector.retrieve(
                    workspace_id=workspace_id,
                    plan=plan,
                    limit=int(
                        self.config.candidate_retrieval["vector_candidate_limit"]
                    ),
                )
            )
        except Exception as error:
            errors["vector"] = type(error).__name__

        allowed, exclusions = self.permissions.filter(candidates, plan)
        ranked = self.ranker.rank(
            allowed,
            max_per_source_object=int(
                self.config.candidate_retrieval["max_chunks_per_source_object"]
            ),
        )[: int(self.config.candidate_retrieval["final_evidence_limit"])]
        request_status = "partial_results" if errors and ranked else "completed"
        if errors and not ranked:
            request_status = "failed"
        versions = {
            "retrieval_config_version": self.config.version,
            "candidate_retrieval_version": str(
                self.config.candidate_retrieval["version"]
            ),
            "ranker_version": str(self.config.ranking["version"]),
            "token_budget_version": str(
                (self.config.token_budget or {}).get("version", "")
            ),
            "final_evidence_limit": str(
                self.config.candidate_retrieval["final_evidence_limit"]
            ),
        }
        payloads = self.builder.build_payloads(
            candidates=ranked,
            permission_exclusions=exclusions,
            token_budget=int(
                (self.config.token_budget or {}).get("max_snippet_tokens", 180)
            ),
            versions=versions,
        )
        payloads["candidate_summary_json"]["errors"] = errors
        evidence_pack = self.evidence.create(
            workspace_id=workspace_id,
            retrieval_request_id=request.id,
            token_budget=int(
                (self.config.token_budget or {}).get("max_evidence_pack_tokens", 4000)
            ),
            ranker_version=str(self.config.ranking["version"]),
            **payloads,
        )
        await self.publisher.publish_created(evidence_pack)
        completed_request = self.requests.mark_completed(
            request.id, status=request_status
        )
        return RetrievalServiceResponse(
            ok=request_status != "failed",
            retrieval_request_id=request.id,
            evidence_pack_id=evidence_pack.id,
            text=self.builder.render_text(evidence_pack),
            evidence_pack=evidence_pack.model_dump(mode="json"),
            status=completed_request.status,
            latency_ms=completed_request.latency_ms,
        )

    async def get_related_work(self, **kwargs: object) -> RetrievalServiceResponse:
        return await self.retrieve_context(**kwargs)  # type: ignore[arg-type]
