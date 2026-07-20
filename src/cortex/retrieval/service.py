from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from cortex.canonical_memory.repositories import InMemoryCanonicalDecisionRepository
from cortex.canonical_memory.retrieval_priority import CanonicalDecisionCandidateAdapter
from cortex.chunking.config import RetrievalConfig
from cortex.embeddings.deterministic import DeterministicEmbeddingProvider
from cortex.interfaces.vector_index import VectorIndex
from cortex.normalization.repositories import InMemoryRelationshipSeedRepository
from cortex.permissions.provider_acls import ProviderAclPrincipal
from cortex.permissions.service import PermissionService
from cortex.utils.asyncio import maybe_await

from .candidates import Candidate
from .evidence import EvidencePackBuilder
from .fts import FtsRetriever
from .hybrid import HybridCandidateFuser
from .permissions import PermissionFilter
from .publishers import EvidencePackPublisher
from .query import QueryPlanner
from .ranking import CandidateRanker
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
        source_chunks: Any,
        vector_index: VectorIndex,
        request_repository: Any,
        evidence_repository: Any,
        publisher: EvidencePackPublisher,
        canonical_decisions: InMemoryCanonicalDecisionRepository | None = None,
        relationship_seeds: InMemoryRelationshipSeedRepository | None = None,
        permission_service: PermissionService | None = None,
        vector_collection: str = "fixture-cortex-dev",
        query_embedder: DeterministicEmbeddingProvider | None = None,
    ) -> None:
        self.config = config
        self.source_chunks = source_chunks
        self.planner = QueryPlanner()
        self.fts = FtsRetriever(source_chunks)
        self.vector = VectorRetriever(
            vector_index=vector_index,
            source_chunks=source_chunks,
            embedder=query_embedder
            or DeterministicEmbeddingProvider(
                dimensions=16, version=config.embeddings.version
            ),
            collection=vector_collection,
        )
        self.requests = request_repository
        self.evidence = evidence_repository
        self.publisher = publisher
        self.canonical_decisions = canonical_decisions
        self.relationship_seeds = relationship_seeds
        self.canonical_adapter = CanonicalDecisionCandidateAdapter()
        self.permission_service = permission_service
        self.builder = EvidencePackBuilder()
        self.ranker = CandidateRanker(config.ranking)
        self.fuser = HybridCandidateFuser()

    async def retrieve_context(
        self,
        *,
        workspace_id: str,
        query: str,
        source_allowlist: list[str] | None = None,
        provider_filters: list[str] | None = None,
        caller_principals: list[ProviderAclPrincipal] | None = None,
    ) -> RetrievalServiceResponse:
        plan = self.planner.plan(
            query=query,
            provider_filters=provider_filters,
            source_allowlist=source_allowlist,
        )
        request = await maybe_await(
            self.requests.create(
                workspace_id=workspace_id,
                query=query,
                filters_json={
                    "provider_filters": plan.provider_filters,
                    "source_allowlist": plan.source_allowlist,
                    "caller_principal_count": len(caller_principals or []),
                },
                source_allowlist_snapshot_hash=plan.source_allowlist_snapshot_hash,
            )
        )
        lexical_candidates: list[Candidate] = []
        vector_candidates: list[Candidate] = []
        additional_candidates: list[Candidate] = []
        errors: dict[str, str] = {}
        try:
            lexical_candidates.extend(
                await self.fts.retrieve(
                    workspace_id=workspace_id,
                    plan=plan,
                    chunking_version=self.config.chunking.version,
                    limit=int(self.config.candidate_retrieval["fts_candidate_limit"]),
                )
            )
        except Exception as error:
            errors["fts"] = type(error).__name__
        try:
            vector_candidates.extend(
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
        if self.canonical_decisions is not None:
            additional_candidates.extend(
                self.canonical_adapter.candidates_for_query(
                    decisions=await maybe_await(
                        self.canonical_decisions.list_active(workspace_id)
                    ),
                    query=query,
                )
            )
        additional_candidates.extend(await self._hint_candidates(workspace_id, plan))
        candidates = self.fuser.fuse(
            workspace_id=workspace_id,
            lexical_candidates=lexical_candidates,
            vector_candidates=vector_candidates,
            provider_filters=plan.provider_filters,
            additional_candidates=additional_candidates,
            limit=int(self.config.candidate_retrieval["merged_candidate_limit"]),
            ranker=self.ranker,
            max_per_source_object=int(
                self.config.candidate_retrieval["max_chunks_per_source_object"]
            ),
        )

        permission_filter = PermissionFilter(
            workspace_id=workspace_id,
            service=self.permission_service,
            caller_principals=caller_principals,
        )
        allowed, exclusions = permission_filter.filter(candidates, plan)
        expanded = await self._expand_relationships(workspace_id, allowed)
        allowed, expansion_exclusions = permission_filter.filter(expanded, plan)
        exclusions = self._merge_exclusions(exclusions, expansion_exclusions)
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
        payloads["candidate_summary_json"]["lexical_candidate_count"] = len(
            lexical_candidates
        )
        payloads["candidate_summary_json"]["vector_candidate_count"] = len(
            vector_candidates
        )
        evidence_pack = await maybe_await(
            self.evidence.create(
                workspace_id=workspace_id,
                retrieval_request_id=request.id,
                token_budget=int(
                    (self.config.token_budget or {}).get(
                        "max_evidence_pack_tokens", 4000
                    )
                ),
                ranker_version=str(self.config.ranking["version"]),
                **payloads,
            )
        )
        await self.publisher.publish_created(evidence_pack)
        completed_request = await maybe_await(
            self.requests.mark_completed(request.id, status=request_status)
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

    async def _hint_candidates(
        self, workspace_id: str, plan: object
    ) -> list[Candidate]:
        if not hasattr(self.source_chunks, "list_all"):
            return []
        chunks = await maybe_await(self.source_chunks.list_all(workspace_id))
        allowed_sources = set(getattr(plan, "source_allowlist", []))
        allowed_providers = {
            provider.lower()
            for provider in getattr(plan, "provider_filters", [])
            if isinstance(provider, str) and provider.strip()
        }
        issue_ids = set(getattr(plan, "issue_ids", []))
        pr_numbers = set(getattr(plan, "pr_numbers", []))
        file_paths = set(getattr(plan, "file_paths", []))
        candidates = []
        for chunk in chunks:
            if allowed_sources and chunk.source_object_id not in allowed_sources:
                continue
            metadata = chunk.metadata_json
            provider = metadata.get("provider")
            if allowed_providers and (
                not isinstance(provider, str)
                or provider.lower() not in allowed_providers
            ):
                continue
            identifier = metadata.get("identifier")
            number = metadata.get("number")
            path = metadata.get("path")
            changed_paths = metadata.get("changed_file_paths")
            if (
                (isinstance(identifier, str) and identifier in issue_ids)
                or (number is not None and str(number) in pr_numbers)
                or (isinstance(path, str) and path in file_paths)
                or (
                    isinstance(changed_paths, list)
                    and any(str(value) in file_paths for value in changed_paths)
                )
            ):
                candidates.append(
                    Candidate(
                        source_chunk=chunk,
                        lexical_score=0.9,
                        relationship_score=0.2,
                        paths={"task_hint"},
                    )
                )
        return candidates

    async def _expand_relationships(
        self, workspace_id: str, candidates: list[Candidate]
    ) -> list[Candidate]:
        if self.relationship_seeds is None:
            return candidates
        source_object_ids = {
            candidate.source_chunk.source_object_id for candidate in candidates
        }
        expanded = list(candidates)
        existing_chunk_ids = {candidate.source_chunk.id for candidate in candidates}
        for seed in await maybe_await(self.relationship_seeds.list_all()):
            if seed.workspace_id != workspace_id:
                continue
            related_id = None
            if seed.from_id in source_object_ids:
                related_id = seed.to_id
            elif seed.to_id in source_object_ids:
                related_id = seed.from_id
            if related_id is None:
                continue
            chunks = await maybe_await(
                self.source_chunks.list_by_source_object(workspace_id, related_id)
            )
            for chunk in chunks:
                if chunk.id in existing_chunk_ids:
                    continue
                existing_chunk_ids.add(chunk.id)
                expanded.append(
                    Candidate(
                        source_chunk=chunk,
                        relationship_score=seed.confidence,
                        paths={f"relationship:{seed.relationship_type}"},
                    )
                )
        return expanded

    def _merge_exclusions(
        self, first: dict[str, int | str], second: dict[str, int | str]
    ) -> dict[str, int | str]:
        excluded_count = int(first.get("excluded_count", 0)) + int(
            second.get("excluded_count", 0)
        )
        reason = first.get("reason") or second.get("reason")
        merged: dict[str, int | str] = {"excluded_count": excluded_count}
        if reason:
            merged["reason"] = str(reason)
        return merged
