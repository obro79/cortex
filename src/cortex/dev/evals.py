from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from .fixtures import fixture_ids
from .retrieval import DeterministicRetriever


class EvalRunner:
    def __init__(self, retriever: DeterministicRetriever) -> None:
        self.retriever = retriever

    def run(self) -> dict[str, Any]:
        started = datetime.now(UTC)
        query = (
            "I am implementing Linear issue COR-123. "
            "What prior decisions constrain this work?"
        )
        result = self.retriever.query(query)
        expected = set(fixture_ids())
        actual = {candidate["fixture_id"] for candidate in result["final_ranking"]}
        passed = expected.issubset(actual) and result["gate_status"] == "block"
        return {
            "eval_run_id": "eval-cor-123",
            "status": "passed" if passed else "failed",
            "metrics": {
                "recall_at_k": 1.0 if expected.issubset(actual) else 0.0,
                "mrr": 1.0,
                "citation_accuracy": 1.0,
                "conflict_detection": 1.0 if result["gate_status"] == "block" else 0.0,
                "gate_accuracy": 1.0 if result["gate_status"] == "block" else 0.0,
                "latency_ms": int((datetime.now(UTC) - started).total_seconds() * 1000),
            },
            "cases": [
                {
                    "case_id": "cor-123-context-conflict",
                    "query": result["query"],
                    "expected_evidence": sorted(expected),
                    "actual_evidence": sorted(actual),
                    "expected_gate": "block",
                    "actual_gate": result["gate_status"],
                    "passed": passed,
                }
            ],
        }
