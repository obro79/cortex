from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from cortex.contracts.entities import EvidencePack, RetrievalRequest
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
    ) -> ContextGateServiceResponse:
        try:
            evidence_pack, retrieval_request = await self._load_or_create_pack(
                workspace_id=workspace_id,
                query=query,
                evidence_pack_id=evidence_pack_id,
                source_allowlist=source_allowlist,
                provider_filters=provider_filters,
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
    ) -> tuple[EvidencePack, RetrievalRequest]:
        if evidence_pack_id:
            pack = self.retrieval_service.evidence.get_by_id(evidence_pack_id)
            request = self.retrieval_service.requests.get_by_id(
                pack.retrieval_request_id
            )
            return pack, request
        if not query:
            raise KeyError("query")
        response = await self.retrieval_service.retrieve_context(
            workspace_id=workspace_id,
            query=query,
            source_allowlist=source_allowlist,
            provider_filters=provider_filters,
        )
        if response.evidence_pack_id is None:
            raise KeyError("evidence_pack")
        pack = self.retrieval_service.evidence.get_by_id(response.evidence_pack_id)
        request = self.retrieval_service.requests.get_by_id(
            response.retrieval_request_id
        )
        return pack, request

    def _signal_json(self, signal: GateSignal) -> dict[str, Any]:
        return {
            "kind": signal.kind,
            "message": signal.message,
            "citation_ids": list(signal.citation_ids),
            "confidence": signal.confidence,
        }
