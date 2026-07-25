from __future__ import annotations

from cortex.context_gate.publishers import ContextGatePublisher
from cortex.context_gate.repositories import InMemoryContextGateResultRepository
from cortex.context_gate.service import ContextGateService
from cortex.events.in_memory import InMemoryEventBus
from cortex.permissions import ProviderAclPrincipal
from cortex.retrieval.defaults import create_empty_retrieval_service
from cortex.retrieval.service import RetrievalServiceResponse
from cortex.retrieval.task_context import TaskContextRequest
from cortex.runtime import CortexAuthority, CortexRuntime, create_local_runtime


class TypedEvidenceRetrieval:
    """A runtime adapter deliberately exposing no repository attributes."""

    def __init__(self, backing: object) -> None:
        self._backing = backing

    async def retrieve_context(self, **kwargs: object):
        return await self._backing.retrieve_context(**kwargs)  # type: ignore[attr-defined, no-any-return]

    async def get_related_work(self, **kwargs: object):
        return await self._backing.get_related_work(**kwargs)  # type: ignore[attr-defined, no-any-return]

    def read_evidence_pack(self, evidence_pack_id: str):
        return self._backing.read_evidence_pack(evidence_pack_id)  # type: ignore[attr-defined, no-any-return]

    def read_retrieval_request(self, retrieval_request_id: str):
        return self._backing.read_retrieval_request(retrieval_request_id)  # type: ignore[attr-defined, no-any-return]


async def test_gate_rejects_evidence_pack_from_another_authority_workspace() -> None:
    runtime = create_local_runtime()
    owner = CortexAuthority(workspace_id="ws_owner", actor_id="owner", trace_id="t1")
    caller = CortexAuthority(workspace_id="ws_caller", actor_id="caller", trace_id="t2")

    retrieval = await runtime.retrieve(authority=owner, query="session migration")
    response = await runtime.check_gate(
        authority=caller, evidence_pack_id=retrieval.evidence_pack_id
    )

    assert response is not None
    assert response.ok is False
    assert response.error == "workspace_scope_mismatch"
    assert response.context_gate_result_id is None


async def test_query_created_gate_propagates_authority_principals() -> None:
    retrieval = create_empty_retrieval_service()
    gate = ContextGateService(
        retrieval_service=retrieval,
        repository=InMemoryContextGateResultRepository(),
        publisher=ContextGatePublisher(InMemoryEventBus()),
    )
    runtime = CortexRuntime(retrieval=retrieval, context_gate=gate, live_data=False)
    principal = ProviderAclPrincipal.from_external_id(
        provider="slack", principal_type="user", external_id="u_1"
    )

    response = await runtime.check_gate(
        authority=CortexAuthority(
            workspace_id="ws_1",
            actor_id="user_1",
            trace_id="trace_1",
            caller_principals=(principal,),
        ),
        query="session migration",
    )

    assert response is not None
    request = await runtime.read_retrieval_request(
        response.result["retrieval_request_id"]  # type: ignore[arg-type]
    )
    assert request.filters_json["caller_principal_count"] == 1


async def test_evidence_bootstrap_uses_typed_runtime_reader() -> None:
    seeded_runtime = create_local_runtime()
    authority = CortexAuthority(workspace_id="ws_1", actor_id="user_1", trace_id="t1")
    retrieval = await seeded_runtime.retrieve(
        authority=authority, query="session migration"
    )
    runtime = CortexRuntime(retrieval=TypedEvidenceRetrieval(seeded_runtime.retrieval))

    evidence_pack = await runtime.evidence_bootstrap(
        authority=authority, evidence_pack_id=retrieval.evidence_pack_id
    )

    assert evidence_pack is not None
    assert evidence_pack["id"] == retrieval.evidence_pack_id


async def test_task_context_forwards_structured_hints_to_query_planning() -> None:
    class CapturingRetrieval:
        def __init__(self) -> None:
            self.query = ""

        async def retrieve_context(self, **kwargs: object) -> RetrievalServiceResponse:
            self.query = str(kwargs["query"])
            return RetrievalServiceResponse(
                ok=True,
                retrieval_request_id="rr_1",
                evidence_pack_id="ep_1",
                text="",
                evidence_pack={
                    "citations_json": {"items": []},
                    "candidate_summary_json": {"errors": {}, "versions": {}},
                    "missing_context_json": {},
                    "conflict_summary_json": {},
                },
                status="completed",
                latency_ms=1,
            )

        async def get_related_work(self, **kwargs: object) -> RetrievalServiceResponse:
            return await self.retrieve_context(**kwargs)

        def read_evidence_pack(self, evidence_pack_id: str) -> object:
            raise KeyError(evidence_pack_id)

        def read_retrieval_request(self, retrieval_request_id: str) -> object:
            raise KeyError(retrieval_request_id)

    retrieval = CapturingRetrieval()
    runtime = CortexRuntime(retrieval=retrieval, live_data=False)
    request = TaskContextRequest.model_validate(
        {
            "task": {
                "objective": "Investigate auth regression",
                "repository": "acme/cortex",
                "branch": "fix/auth",
                "issue_ids": ["COR-123"],
                "pull_request_numbers": [42],
                "file_hints": ["src/cortex/runtime/context.py"],
            }
        }
    )

    await runtime.get_task_context(
        authority=CortexAuthority(
            workspace_id="ws_1", actor_id="actor_1", trace_id="trace_1"
        ),
        request=request,
    )

    assert "Investigate auth regression" in retrieval.query
    assert "COR-123" in retrieval.query
    assert "#42" in retrieval.query
    assert "src/cortex/runtime/context.py" in retrieval.query
