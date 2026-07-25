# Operations Evidence

This directory stores dated evidence for restore, rollback, load, and cost
drills, plus local implementation evidence that explicitly distinguishes itself
from staging or production drill proof.

Evidence entries must state:

- environment,
- operator,
- commit or image under test,
- commands or systems exercised,
- result,
- residual risk,
- follow-up owner.

Do not record production customer data, raw provider payloads, tokens, private
URLs, or unredacted object identifiers.

Local no-secret gate evidence can be generated with:

```bash
uv run python scripts/backend_ops_launch_gate.py --evidence docs/operations/evidence/<date>-backend-ops-launch-gate-local-evidence.md
```

Local gate evidence must keep the `not staging evidence` marker unless the
commands were run against deployed staging or production systems.
