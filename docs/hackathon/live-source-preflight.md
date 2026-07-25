# Live-source demo preflight

Run `uv run python scripts/live_sources_preflight.py --format json` before a
credentialed Slack/GitHub demo. It only reports whether required environment
variables are present; it neither prints their values nor makes provider calls.

The report is not evidence of a live sync. After it passes, an operator must use
approved Slack channels and GitHub repository/source-connection bindings, then
run the controlled manual webhook/backfill smoke with the real runtime. Record
provider responses, durable pipeline counts, and any failure separately from the
fixture-only Slack and GitHub smoke scripts.
