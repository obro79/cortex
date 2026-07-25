from __future__ import annotations

from cortex.contracts.entities import ContextGateResult


class GateMessageRenderer:
    def render(self, result: ContextGateResult) -> str:
        reasons = result.reasons_json.get("items", [])
        lines = [f"context gate: {result.status} ({result.risk_category})"]
        if isinstance(reasons, list):
            for reason in reasons[:3]:
                if not isinstance(reason, dict):
                    continue
                message = str(reason.get("message", "reason recorded"))
                citations = reason.get("citation_ids", [])
                cite_text = ""
                if isinstance(citations, list) and citations:
                    cite_text = " " + " ".join(
                        f"[{citation}]" for citation in citations[:3]
                    )
                lines.append(f"- {message}{cite_text}")
        actions = result.required_actions_json.get("actions", [])
        if isinstance(actions, list) and actions:
            lines.append("actions: " + ", ".join(str(action) for action in actions))
        return "\n".join(lines[:6])
