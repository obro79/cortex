from __future__ import annotations

from cortex.contracts.entities import CanonicalDecision


class CanonicalDecisionRenderer:
    def render_proposal(self, decision: CanonicalDecision) -> str:
        return (
            f"canonical proposal: {decision.status} ({decision.scope_type}:"
            f"{decision.scope_ref})\n- {decision.title}"
        )

    def render_approval(self, decision: CanonicalDecision, action: str) -> str:
        return f"canonical decision: {decision.status} ({action})\n- {decision.title}"
