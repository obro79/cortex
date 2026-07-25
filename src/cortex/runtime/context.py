from __future__ import annotations

from collections.abc import Awaitable
from dataclasses import dataclass
from inspect import isawaitable
from typing import Protocol, cast

from cortex.context_gate.service import ContextGateService, ContextGateServiceResponse
from cortex.contracts.entities import EvidencePack, RetrievalRequest
from cortex.permissions import ProviderAclPrincipal
from cortex.retrieval.defaults import create_empty_retrieval_service
from cortex.retrieval.service import RetrievalService, RetrievalServiceResponse


@dataclass(frozen=True)
class CortexAuthority:
    """Authority resolved by a trusted transport adapter, never tool input."""

    workspace_id: str
    actor_id: str | None
    trace_id: str
    caller_principals: tuple[ProviderAclPrincipal, ...] = ()


class ContextRetrieval(Protocol):
    async def retrieve_context(
        self,
        *,
        workspace_id: str,
        query: str,
        source_allowlist: list[str] | None = None,
        provider_filters: list[str] | None = None,
        caller_principals: list[ProviderAclPrincipal] | None = None,
    ) -> RetrievalServiceResponse: ...

    async def get_related_work(self, **kwargs: object) -> RetrievalServiceResponse: ...

    def read_evidence_pack(
        self, evidence_pack_id: str
    ) -> EvidencePack | Awaitable[EvidencePack]: ...

    def read_retrieval_request(
        self, retrieval_request_id: str
    ) -> RetrievalRequest | Awaitable[RetrievalRequest]: ...


class InMemoryContextRetrievalAdapter:
    """Typed adapter for the deterministic retrieval fixture.

    Durable runtime adapters implement :class:`ContextRetrieval` directly and
    may make the read methods async.  Keeping the repository reach-through in
    this fixture-only adapter prevents it from leaking across the runtime
    authority boundary.
    """

    def __init__(self, retrieval: RetrievalService) -> None:
        self._retrieval = retrieval

    async def retrieve_context(self, **kwargs: object) -> RetrievalServiceResponse:
        return await self._retrieval.retrieve_context(**kwargs)  # type: ignore[arg-type]

    async def get_related_work(self, **kwargs: object) -> RetrievalServiceResponse:
        return await self._retrieval.get_related_work(**kwargs)

    def read_evidence_pack(self, evidence_pack_id: str) -> EvidencePack:
        return self._retrieval.evidence.get_by_id(evidence_pack_id)

    def read_retrieval_request(self, retrieval_request_id: str) -> RetrievalRequest:
        return self._retrieval.requests.get_by_id(retrieval_request_id)


@dataclass
class CortexRuntime:
    """One injected context boundary for API and MCP adapters.

    Durable retrieval implementations are supplied by the composition root.  The
    local factory is deliberately only a development fallback.
    """

    retrieval: ContextRetrieval | RetrievalService
    context_gate: ContextGateService | None = None
    live_data: bool = True

    def __post_init__(self) -> None:
        # Existing local callers inject RetrievalService directly.  Normalize
        # that fixture here; production adapters must provide ContextRetrieval.
        if isinstance(self.retrieval, RetrievalService):
            self.retrieval = InMemoryContextRetrievalAdapter(self.retrieval)

    def _context_retrieval(self) -> ContextRetrieval:
        return cast(ContextRetrieval, self.retrieval)

    async def retrieve(
        self,
        *,
        authority: CortexAuthority,
        query: str,
        source_allowlist: list[str] | None = None,
        provider_filters: list[str] | None = None,
        related: bool = False,
    ) -> RetrievalServiceResponse:
        retrieval = self._context_retrieval()
        method = (
            retrieval.get_related_work
            if related
            else retrieval.retrieve_context
        )
        return await method(
            workspace_id=authority.workspace_id,
            query=query,
            source_allowlist=source_allowlist,
            provider_filters=provider_filters,
            caller_principals=list(authority.caller_principals),
        )

    async def check_gate(
        self,
        *,
        authority: CortexAuthority,
        query: str | None = None,
        evidence_pack_id: str | None = None,
        task_hints: dict[str, object] | None = None,
        source_allowlist: list[str] | None = None,
        provider_filters: list[str] | None = None,
    ) -> ContextGateServiceResponse | None:
        if self.context_gate is None:
            return None
        return await self.context_gate.check_context_gate(
            workspace_id=authority.workspace_id,
            query=query,
            evidence_pack_id=evidence_pack_id,
            task_hints=task_hints,
            source_allowlist=source_allowlist,
            provider_filters=provider_filters,
            caller_principals=list(authority.caller_principals),
            evidence_reader=self,
        )

    async def read_evidence_pack(self, evidence_pack_id: str) -> EvidencePack:
        """Read through the declared adapter contract, including async stores."""
        result = self._context_retrieval().read_evidence_pack(evidence_pack_id)
        if isawaitable(result):
            result = await result
        return result

    async def read_retrieval_request(
        self, retrieval_request_id: str
    ) -> RetrievalRequest:
        """Read through the declared adapter contract, including async stores."""
        result = self._context_retrieval().read_retrieval_request(
            retrieval_request_id
        )
        if isawaitable(result):
            result = await result
        return result

    def evidence_bootstrap(
        self, *, authority: CortexAuthority, evidence_pack_id: str
    ) -> dict[str, object] | None:
        """Load an evidence pack only when it belongs to the derived workspace."""
        try:
            evidence_pack = self._context_retrieval().read_evidence_pack(
                evidence_pack_id
            )
        except KeyError:
            return None
        # This synchronous compatibility endpoint is served by the in-memory
        # fixture. Durable adapters are supported by the async read methods
        # used by authority-sensitive gate evaluation.
        if isawaitable(evidence_pack):
            return None
        if getattr(evidence_pack, "workspace_id", None) != authority.workspace_id:
            return None
        return cast(dict[str, object], evidence_pack.model_dump(mode="json"))


def create_local_runtime() -> CortexRuntime:
    """Build the explicit deterministic fallback used by local CLI/test adapters."""
    from cortex.context_gate.publishers import ContextGatePublisher
    from cortex.context_gate.repositories import InMemoryContextGateResultRepository
    from cortex.events.in_memory import InMemoryEventBus

    retrieval = create_empty_retrieval_service()
    return CortexRuntime(
        retrieval=retrieval,
        context_gate=ContextGateService(
            retrieval_service=retrieval,
            repository=InMemoryContextGateResultRepository(),
            publisher=ContextGatePublisher(InMemoryEventBus()),
        ),
        live_data=False,
    )
