"""Fixture-safe audience evidence for the Cortex demo."""

from .control_plane import DemoEvidenceControlPlane, DemoEvidenceReport
from .evidence_contract import (
    EvidenceCitation,
    EvidenceContractEvaluator,
    EvidenceContractFailure,
    EvidenceContractPolicy,
    EvidenceContractReport,
)
from .golden_incident import (
    GoldenIncidentManifest,
    GoldenIncidentRecord,
    expected_counts,
    load_golden_incident_manifest,
)
from .seed import (
    DemoCorpusSeeder,
    DemoResetScope,
    DemoSeedResult,
    InMemoryDemoRuntime,
    inputs_for_phase,
    reset_scope,
)

__all__ = [
    "DemoEvidenceControlPlane",
    "DemoEvidenceReport",
    "GoldenIncidentManifest",
    "GoldenIncidentRecord",
    "EvidenceCitation",
    "EvidenceContractEvaluator",
    "EvidenceContractFailure",
    "EvidenceContractPolicy",
    "EvidenceContractReport",
    "expected_counts",
    "DemoCorpusSeeder",
    "DemoResetScope",
    "DemoSeedResult",
    "InMemoryDemoRuntime",
    "inputs_for_phase",
    "load_golden_incident_manifest",
    "reset_scope",
]
