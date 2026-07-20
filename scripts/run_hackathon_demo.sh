#!/usr/bin/env bash
set -euo pipefail

# The fixture workbench and audience-facing evidence endpoint are deliberately
# local/test-only. This launcher makes that boundary explicit.
export CORTEX_DEV_WORKBENCH_ENABLED=true

exec uv run --extra dev uvicorn cortex.api.app:create_app --factory \
  --host "${CORTEX_DEMO_HOST:-127.0.0.1}" \
  --port "${CORTEX_DEMO_PORT:-8000}"
