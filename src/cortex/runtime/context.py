from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, cast

from cortex.context_gate.service import ContextGateService, ContextGateServiceResponse
from cortex.permissions import ProviderAclPrincipal
from cortex.retrieval.defaults import create_empty_retrieval_service
from cortex.retrieval.service import RetrievalServiceResponse


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


@dataclass
class CortexRuntime:
    """One injected context boundary for API and MCP adapters.

    Durable retrieval implementations are supplied by the composition root.  The
    local factory is deliberately only a development fallback.
    """

    retrieval: ContextRetrieval
    context_gate: ContextGateService | None = None
    live_data: bool = True

    async def retrieve(
        self,
        *,
        authority: CortexAuthority,
        query: str,
        source_allowlist: list[str] | None = None,
        provider_filters: list[str] | None = None,
        related: bool = False,
    ) -> RetrievalServiceResponse:
        method = (
            self.retrieval.get_related_work
            if related
            else self.retrieval.retrieve_context
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
        )

    def evidence_bootstrap(
        self, *, authority: CortexAuthority, evidence_pack_id: str
    ) -> dict[str, object] | None:
        """Load an evidence pack only when it belongs to the derived workspace."""
        repository = getattr(self.retrieval, "evidence", None)
        get_by_id = getattr(repository, "get_by_id", None)
        if not callable(get_by_id):
            return None
        try:
            evidence_pack = get_by_id(evidence_pack_id)
        except KeyError:
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
