from __future__ import annotations

from collections.abc import Awaitable
from dataclasses import dataclass
from inspect import isawaitable
from typing import Any, Protocol

from cortex.contracts.entities import EvidencePack, RetrievalRequest
from cortex.permissions import ProviderAclPrincipal
from cortex.retrieval.service import RetrievalService

from .decision import GateDecisionEngine
from .publishers import ContextGatePublisher
from .render import GateMessageRenderer
from .repositories import InMemoryContextGateResultRepository
from .risk import RiskClassifier
from .signals import EvidenceSignalExtractor, GateSignal


@dataclass(frozen=True)
class ContextGateServiceResponse:
    ok: bool
    context_gate_result_id: str | None
    status: str
    text: str
    result: dict[str, object]
    error: str | None = None


class EvidencePackReader(Protocol):
    """Runtime-owned evidence reads, backed by either memory or durable state."""

    def read_evidence_pack(
        self, evidence_pack_id: str
    ) -> EvidencePack | Awaitable[EvidencePack]: ...

    def read_retrieval_request(
        self, retrieval_request_id: str
    ) -> RetrievalRequest | Awaitable[RetrievalRequest]: ...


class ContextGateService:
    def __init__(
        self,
        *,
        retrieval_service: RetrievalService,
        repository: InMemoryContextGateResultRepository,
        publisher: ContextGatePublisher,
    ) -> None:
        self.retrieval_service = retrieval_service
        self.repository = repository
        self.publisher = publisher
        self.risk_classifier = RiskClassifier()
        self.signal_extractor = EvidenceSignalExtractor()
        self.decision_engine = GateDecisionEngine()
        self.renderer = GateMessageRenderer()

    async def check_context_gate(
        self,
        *,
        workspace_id: str,
        query: str | None = None,
        evidence_pack_id: str | None = None,
        task_hints: dict[str, object] | None = None,
        source_allowlist: list[str] | None = None,
        provider_filters: list[str] | None = None,
        caller_principals: list[ProviderAclPrincipal] | None = None,
        evidence_reader: EvidencePackReader | None = None,
    ) -> ContextGateServiceResponse:
        try:
            evidence_pack, retrieval_request = await self._load_or_create_pack(
                workspace_id=workspace_id,
                query=query,
                evidence_pack_id=evidence_pack_id,
                source_allowlist=source_allowlist,
                provider_filters=provider_filters,
                caller_principals=caller_principals,
                evidence_reader=evidence_reader,
            )
        except KeyError:
            return ContextGateServiceResponse(
                ok=False,
                context_gate_result_id=None,
                status="failed",
                text="context gate: failed (evidence pack not found)",
                result={},
                error="evidence_pack_not_found",
            )
        if (
            evidence_pack.workspace_id != workspace_id
            or retrieval_request.workspace_id != workspace_id
        ):
            return ContextGateServiceResponse(
                ok=False,
                context_gate_result_id=None,
                status="failed",
                text="context gate: failed (evidence pack workspace mismatch)",
                result={},
                error="workspace_scope_mismatch",
            )

        evaluating = self.repository.create_evaluating(
            workspace_id=evidence_pack.workspace_id,
            retrieval_request_id=evidence_pack.retrieval_request_id,
            evidence_pack_id=evidence_pack.id,
            gate_version=self.retrieval_service.config.context_gate.version,
        )
        risk = self.risk_classifier.classify(
            query=query or retrieval_request.query,
            evidence_pack=evidence_pack,
            retrieval_request=retrieval_request,
            task_hints=task_hints,
        )
        signals = self.signal_extractor.extract(evidence_pack)
        decision = self.decision_engine.decide(
            config=self.retrieval_service.config.context_gate,
            risk=risk,
            signals=signals,
        )
        result = self.repository.complete(
            evaluating.id,
            status=decision.status,
            risk_category=decision.risk_category,
            reasons_json={
                "items": [self._signal_json(signal) for signal in decision.reasons]
            },
            required_actions_json={"actions": list(decision.required_actions)},
        )
        await self.publisher.publish_completed(result)
        text = self.renderer.render(result)
        return ContextGateServiceResponse(
            ok=decision.status != "failed",
            context_gate_result_id=result.id,
            status=str(result.status),
            text=text,
            result=result.model_dump(mode="json"),
        )

    async def _load_or_create_pack(
        self,
        *,
        workspace_id: str,
        query: str | None,
        evidence_pack_id: str | None,
        source_allowlist: list[str] | None,
        provider_filters: list[str] | None,
        caller_principals: list[ProviderAclPrincipal] | None,
        evidence_reader: EvidencePackReader | None,
    ) -> tuple[EvidencePack, RetrievalRequest]:
        reader = evidence_reader or _RetrievalServiceEvidenceReader(
            self.retrieval_service
        )
        if evidence_pack_id:
            pack = await self._read_evidence_pack(reader, evidence_pack_id)
            request = await self._read_retrieval_request(
                reader, pack.retrieval_request_id
            )
            return pack, request
        if not query:
            raise KeyError("query")
        response = await self.retrieval_service.retrieve_context(
            workspace_id=workspace_id,
            query=query,
            source_allowlist=source_allowlist,
            provider_filters=provider_filters,
            caller_principals=caller_principals,
        )
        if response.evidence_pack_id is None:
            raise KeyError("evidence_pack")
        pack = await self._read_evidence_pack(reader, response.evidence_pack_id)
        request = await self._read_retrieval_request(
            reader, response.retrieval_request_id
        )
        return pack, request

    async def _read_evidence_pack(
        self, reader: EvidencePackReader, evidence_pack_id: str
    ) -> EvidencePack:
        result = reader.read_evidence_pack(evidence_pack_id)
        if isawaitable(result):
            result = await result
        return result

    async def _read_retrieval_request(
        self, reader: EvidencePackReader, retrieval_request_id: str
    ) -> RetrievalRequest:
        result = reader.read_retrieval_request(retrieval_request_id)
        if isawaitable(result):
            result = await result
        return result

    def _signal_json(self, signal: GateSignal) -> dict[str, Any]:
        return {
            "kind": signal.kind,
            "message": signal.message,
            "citation_ids": list(signal.citation_ids),
            "confidence": signal.confidence,
        }


class _RetrievalServiceEvidenceReader:
    """Legacy adapter for direct deterministic ContextGateService fixtures."""

    def __init__(self, retrieval_service: RetrievalService) -> None:
        self._retrieval_service = retrieval_service

    def read_evidence_pack(self, evidence_pack_id: str) -> EvidencePack:
        return self._retrieval_service.evidence.get_by_id(evidence_pack_id)

    def read_retrieval_request(self, retrieval_request_id: str) -> RetrievalRequest:
        return self._retrieval_service.requests.get_by_id(retrieval_request_id)
