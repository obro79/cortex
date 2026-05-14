# 2026-05-14 Shared Connector Setup Service Slice

## Completed

- Added a provider-neutral connector setup service for Slack, GitHub, Linear,
  and repo docs service adapters.
- Added normalized setup overview and health read-model output.
- Added provider data-read explanation content for setup UI/API surfaces.
- Added source-selection authorization helper.
- Gated setup, source selection, reauth, revoke, and backfill retry actions
  through workspace admin authorization.
- Audited allowed and denied connector actions with existing redaction for
  tokens, secrets, private URLs, and raw payload-like metadata.

## Validation

```bash
uv run pytest tests/connectors/test_setup_service.py tests/security/test_admin_authorization.py tests/security/test_redaction.py
uv run ruff check src/cortex/connectors/setup.py src/cortex/connectors/__init__.py tests/connectors/test_setup_service.py
```

Result: both passed.

## Remaining Phase 16 Work

- Wire setup service into public UI/API routes after Phase 15 onboarding routes
  are complete.
- Add provider-specific install/callback/revoke/reauth routes for Slack and
  GitHub.
- Add backfill enqueue/status integration for selected sources.
- Add browser smoke coverage for Slack and GitHub setup.
