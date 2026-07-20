# Live Context Proof operator runbook

## Safety boundary

Run one approved Slack channel in one workspace. Cortex must retain canonical
SQL state and Qdrant must be a derived index. Do not paste secrets into a shell
history, report, ticket, or chat. Do not record message text, query text, URLs,
raw Slack IDs, or access tokens in the evidence packet.

## Before credentials are available

```bash
uv run python scripts/live_context_preflight.py --format json
docker compose config --quiet
```

Use the report's `next_action`. A non-zero preflight is expected until settings
are configured; it is not an outage.

## Controlled run

1. Configure secrets locally, complete the approved Slack OAuth installation,
   and select exactly one channel.
2. Start local dependencies and run the explicit migrate service. Verify the
   migration revision separately; preflight never mutates schema.
3. Trigger the selected-source backfill. Confirm a durable raw-event count,
   then normalization, chunk, embedding, and index completion counts.
4. Verify the same number of intended derived points in the resolved Qdrant
   collection. Do not use Qdrant as authority for access or source truth.
5. Issue one authenticated `get_task_context` request with an allowed caller.
   Record only the request count, evidence-pack count, and status code.
6. Save a redacted report and validate it:

   ```bash
   uv run python scripts/live_context_preflight.py --validate-report PATH_TO_REPORT.json
   ```

7. Repeat once after restart/idempotent replay. Record aggregate counts and
   stage statuses only.

## Fail closed

Stop and mark the report `failed` if source selection changes, workspace or ACL
checks fail, schema is not current, a vector cannot be verified, or a caller
sees evidence outside their allowed scope. Never claim a live proof from the
fixture demo report.

## Runtime/reporting integration handoff

The runtime owner should emit `live-context-run-report/v1` only after the final
pipeline and task-context stages finish. Use opaque hashes for run/source refs,
the resolved Qdrant collection name, integer counters, freshness seconds, and
status codes. Validate the serialized JSON with the command above before adding
it to the demo packet.

The SQL `demo_run_reports` projection can now durably store that validated,
redacted snapshot and the read-only control plane will return it after restart.
It deliberately does **not** derive a report from current workspace-wide rows:
doing that could mix unrelated runs. Before a report can be emitted
automatically, the runtime still needs the exact run-membership ledger/finalizer
described in the Live Context Proof specification. Until then, no stored report
is evidence of a completed live run by itself.
