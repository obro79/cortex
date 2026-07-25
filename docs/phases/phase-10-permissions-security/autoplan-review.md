# Phase 10 Autoplan Review

## Review Scope

Plan reviewed:

- [`plan.md`](plan.md)
- [`implementation-checklist.md`](implementation-checklist.md)
- [`test-plan.md`](test-plan.md)
- Phase 10 roadmap,
- source allowlist ADR,
- secrets/token ADR,
- webhook security ADR,
- retrieval/evidence and context-gate plans,
- Phase 8.5 manual security review pattern,
- Phase 9 source expansion plan.

Autoplan mode:

- CEO review: production trust gate.
- Design review: safe, understandable source coverage/debug output.
- Engineering review: enforcement points, secrets, audit logs, redaction.
- DX review: focused security test loop and review evidence.

## Executive Verdict

Phase 10 is approved as the production-trust hardening phase. It should not
expand into full enterprise auth. Its job is to make v1 source allowlists,
secret boundaries, debug output, and audit logs consistently safe.
It must still include a minimal admin authorization gate for security-sensitive
actions; audit alone is not enough.

## CEO Review

Score: 9/10.

| Premise | Verdict | Reasoning |
| --- | --- | --- |
| This phase is required before real customer data. | Accepted | Connector breadth without privacy hardening is not credible. |
| Source allowlists remain the v1 permission model. | Accepted with risk | Good enough if fail-closed and redaction tests are strict. |
| Full provider-native ACLs can wait. | Accepted | Too expensive for v1; model/snapshots should be later-ready. |
| Debug output must be audited. | Accepted | Most early leaks happen in diagnostics, not core retrieval. |
| Audit alone is sufficient for admin actions. | Rejected | Security-sensitive actions need a minimal admin actor check. |

## Design Review

Score: 8/10.

Safe output still needs to be useful. Source coverage should explain that
sources were excluded without naming hidden repos/channels/teams/docs roots.
Debug screens and MCP outputs should provide trace IDs, counts, statuses, and
safe categories rather than raw hidden identifiers.

## Engineering Review

Score: 9/10.

```txt
source allowlist
  -> central permission service
  -> ingestion/replay/retrieval/debug enforcement
  -> redaction service
  -> audit log
  -> security review report
```

Key decisions:

1. Permission checks must fail closed.
2. Allowlist filtering must happen before candidate ranking and evidence
   rendering.
3. Debug/source coverage/deadletter output is part of the privacy boundary.
4. Secret material must never leave `SecretRef`.
5. Audit logs are append-only and sanitized.
6. Security-sensitive admin actions require an authorized admin actor.

## DX Review

Score: 8/10.

The focused loop should be:

```txt
pytest tests/permissions tests/security tests/retrieval tests/context_gate
```

The final review report should include exact commands, redaction scans, drills,
and a clear approve/block decision.

## Risks

| Risk | Mitigation |
| --- | --- |
| Permission checks are duplicated inconsistently. | Central permission service. |
| Debug endpoints leak hidden metadata. | Debug redaction audit and tests. |
| Source coverage reveals hidden source names. | Aggregate counts only. |
| Allowlist removal leaves stale vectors/search rows. | Immediate retrieval block plus cleanup jobs. |
| Secret material appears in audit/logs. | Secret boundary tests and redaction scans. |
| Identity mapping looks like full ACL enforcement. | Explicit later-ready model, not enforcement. |
| Admin/security action is only audited, not gated. | Minimal admin authorization service. |

## Final Approval Gate

Approved to implement if:

- source allowlists stay the v1 enforcement model,
- all enforcement points are covered,
- redaction/debug audit is required,
- secret scans include run artifacts,
- final security report decides `APPROVED_FOR_REAL_CUSTOMER_DATA` or `BLOCKED`.
- security-sensitive admin actions are permission-gated, not just audited.
