from cortex.chunking.config import load_retrieval_config
from cortex.context_gate.decision import GateDecisionEngine
from cortex.context_gate.risk import RiskClassifier
from cortex.context_gate.signals import EvidenceSignalExtractor
from cortex.contracts.enums import ContextGateStatus

from .helpers import make_pack, make_request


def decide(query: str, **pack_kwargs: object) -> tuple[ContextGateStatus, str]:
    pack = make_pack(**pack_kwargs)
    request = make_request(query)
    risk = RiskClassifier().classify(
        query=query, evidence_pack=pack, retrieval_request=request
    )
    signals = EvidenceSignalExtractor().extract(pack)
    decision = GateDecisionEngine().decide(
        config=load_retrieval_config().context_gate,
        risk=risk,
        signals=signals,
    )
    return decision.status, decision.risk_category


def test_architecture_conflict_blocks() -> None:
    status, risk = decide("COR-123 session storage", conflict_count=1)

    assert status == ContextGateStatus.BLOCK
    assert risk == "architecture_conflict"


def test_low_risk_missing_context_warns() -> None:
    status, risk = decide("maybe update copy", missing_count=1)

    assert status == ContextGateStatus.WARN
    assert risk == "missing_task_context"


def test_clear_current_evidence_allows() -> None:
    status, risk = decide("update button label")

    assert status == ContextGateStatus.ALLOW
    assert risk == "clear_context"


def test_permission_ambiguity_blocks() -> None:
    status, risk = decide(
        "update permissions",
        permission_exclusions={"excluded_count": 1},
    )

    assert status == ContextGateStatus.BLOCK
    assert risk == "permission_sensitive_ambiguity"


def test_uncited_conflict_fails_instead_of_blocking() -> None:
    status, _risk = decide("COR-123 session storage", conflict_count=1, citations=[])

    assert status == ContextGateStatus.FAILED
