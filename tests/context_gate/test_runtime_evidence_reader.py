from __future__ import annotations

from cortex.context_gate.publishers import ContextGatePublisher
from cortex.context_gate.repositories import InMemoryContextGateResultRepository
from cortex.context_gate.service import ContextGateService
from cortex.events.in_memory import InMemoryEventBus
from cortex.retrieval.defaults import create_empty_retrieval_service

from .helpers import make_pack, make_request


class AsyncEvidenceReader:
    async def read_evidence_pack(self, evidence_pack_id: str):
        assert evidence_pack_id == "ep_1"
        return make_pack()

    async def read_retrieval_request(self, retrieval_request_id: str):
        assert retrieval_request_id == "ret_1"
        return make_request()


async def test_gate_accepts_async_typed_evidence_reader() -> None:
    service = ContextGateService(
        retrieval_service=create_empty_retrieval_service(),
        repository=InMemoryContextGateResultRepository(),
        publisher=ContextGatePublisher(InMemoryEventBus()),
    )

    response = await service.check_context_gate(
        workspace_id="ws_1",
        evidence_pack_id="ep_1",
        evidence_reader=AsyncEvidenceReader(),
    )

    assert response.ok is True
    assert response.context_gate_result_id is not None
