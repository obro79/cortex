from __future__ import annotations

from dataclasses import dataclass

from cortex.chunking.config import ContextGateConfig
from cortex.contracts.enums import ContextGateStatus

from .risk import RiskClassification
from .signals import GateSignal

BLOCK_ACTIONS = (
    "approve",
    "edit",
    "proceed_with_warning",
    "mark_unresolved",
    "stop",
)


@dataclass(frozen=True)
class GateDecision:
    status: ContextGateStatus
    risk_category: str
    reasons: tuple[GateSignal, ...]
    required_actions: tuple[str, ...] = ()


class GateDecisionEngine:
    def decide(
        self,
        *,
        config: ContextGateConfig,
        risk: RiskClassification,
        signals: list[GateSignal],
    ) -> GateDecision:
        warn_or_block = [
            signal for signal in signals if signal.kind != "source_coverage"
        ]
        uncited = [
            signal
            for signal in warn_or_block
            if signal.kind != "clear_context" and not signal.citation_ids
        ]
        if uncited:
            return GateDecision(
                status=ContextGateStatus.FAILED,
                risk_category=risk.category,
                reasons=tuple(uncited),
            )

        permission = self._signals(signals, "permission_ambiguity")
        if permission and config.block_on_permission_uncertainty:
            return GateDecision(
                status=ContextGateStatus.BLOCK,
                risk_category="permission_sensitive_ambiguity",
                reasons=tuple(permission),
                required_actions=BLOCK_ACTIONS,
            )

        conflicts = [
            signal
            for signal in self._signals(signals, "conflict")
            if signal.confidence >= config.high_confidence_conflict_threshold
        ]
        if conflicts and config.block_on_high_confidence_architecture_conflict:
            return GateDecision(
                status=ContextGateStatus.BLOCK,
                risk_category="architecture_conflict",
                reasons=tuple(conflicts),
                required_actions=BLOCK_ACTIONS,
            )

        coverage = next(
            (signal for signal in signals if signal.kind == "source_coverage"), None
        )
        if risk.high_risk and coverage is not None:
            source_count = int(coverage.message.split(" ", 1)[0])
            if source_count < config.min_required_sources_for_high_risk_tasks:
                return GateDecision(
                    status=ContextGateStatus.BLOCK,
                    risk_category=risk.category,
                    reasons=(coverage,),
                    required_actions=BLOCK_ACTIONS,
                )

        missing = self._signals(signals, "missing_context")
        stale = self._signals(signals, "stale_context")
        if missing and (
            config.warn_on_missing_low_risk_context
            or risk.category == "low_risk_ambiguity"
        ):
            return GateDecision(
                status=ContextGateStatus.WARN,
                risk_category=risk.category,
                reasons=tuple(missing),
            )
        if stale:
            return GateDecision(
                status=ContextGateStatus.WARN,
                risk_category="stale_context",
                reasons=tuple(stale),
            )

        clear = self._signals(signals, "clear_context")
        return GateDecision(
            status=ContextGateStatus.ALLOW,
            risk_category=risk.category,
            reasons=tuple(clear or signals[:1]),
        )

    def _signals(self, signals: list[GateSignal], kind: str) -> list[GateSignal]:
        return [signal for signal in signals if signal.kind == kind]
