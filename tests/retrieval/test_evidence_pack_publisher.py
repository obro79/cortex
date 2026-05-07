from datetime import UTC, datetime

from cortex.contracts.entities import EvidencePack
from cortex.contracts.enums import EvidencePackStatus
from cortex.events.in_memory import InMemoryEventBus
from cortex.retrieval.publishers import EvidencePackPublisher


async def test_evidence_pack_created_envelope_is_pointer_only() -> None:
    now = datetime.now(UTC)
    pack = EvidencePack(
        id="ep_1",
        workspace_id="ws_1",
        retrieval_request_id="ret_1",
        status=EvidencePackStatus.CREATED,
        claims_json={},
        citations_json={"items": [{"snippet": "sensitive snippet"}]},
        candidate_summary_json={"candidate_count": 1},
        source_coverage_json={},
        permission_exclusions_json={},
        missing_context_json={},
        stale_context_json={},
        conflict_summary_json={},
        token_budget=4000,
        ranker_version="ranking-v1",
        created_at=now,
    )
    envelope = await EvidencePackPublisher(InMemoryEventBus()).publish_created(pack)

    assert envelope.event_type == "evidence_pack.created"
    assert envelope.subject.type == "evidence_pack"
    assert envelope.causation.retrieval_request_id == "ret_1"
    assert "snippet" not in envelope.payload
