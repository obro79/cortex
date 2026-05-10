# Phase 14 Test Plan

## Focus

Phase 14 testing proves that the minimal UI reads real data, respects
permissions, audits sensitive actions, and remains usable for source health and
evidence inspection.

## Automated Test Targets

Suggested focused files:

- `tests/api/test_ui_guard.py`
- `tests/ui/test_page_shell.py`
- `tests/ui/test_source_health_page.py`
- `tests/ui/test_evidence_pack_inspector.py`
- `tests/ui/test_canonical_decision_history.py`
- `tests/ui/test_conflict_list.py`
- `tests/ui/test_connector_setup.py`
- `tests/ui/test_backfill_replay_status.py`
- `tests/ui/test_ui_action_audit.py`
- `tests/ui/test_ui_workspace_isolation.py`
- `tests/ui/test_ui_pagination.py`
- `tests/ui/test_ui_accessibility.py`
- `tests/ui/test_ui_seed.py`
- `tests/e2e/test_minimal_ui_smoke.py`

## Required Coverage

### Route Guard

- Unauthenticated requests cannot access UI pages.
- Missing workspace context is handled safely.
- Non-admin actors can view only allowed read surfaces.
- Non-admin actors cannot perform setup, replay, re-sync, re-index, or approval
  actions.
- Denied attempts create audit records.
- UI routes are unavailable when the UI feature flag is disabled.
- Internal admin session mode is disabled by default.
- Mutating UI actions require CSRF tokens.
- Invalid CSRF tokens are denied and audited for sensitive actions.

### Persistent Seed

- Seed creates a dedicated test workspace.
- Seed writes source, source health, evidence, canonical decision, conflict, and
  job data through repositories/services.
- Seed creates admin and non-admin actors.
- Reset removes only the test workspace data.
- Browser smoke tests do not depend on `/dev/workbench` in-memory state.

### Shared UI Actions

- All mutating UI actions use the shared action contract.
- Action responses include audit event ID and trace ID.
- Asynchronous actions include job ID.
- Duplicate idempotency keys do not enqueue duplicate work.
- Action responses redact provider secrets, tokens, private content, and raw
  provider payloads.

### Source Health

- Page reads real source/connector health data.
- Fresh, stale, failing, disabled, and reauthorization-needed states render.
- Re-sync/backfill action enqueues work and returns a job reference.
- Empty state is accurate when no sources exist.
- Rows are scoped to the active workspace.
- Lists are paginated or bounded with deterministic ordering.

### Evidence-Pack Inspector

- List/detail pages read real evidence-pack records.
- Gate status, reasons, source coverage, citations, stale/conflict signals, and
  permission exclusions render.
- Private or disallowed content is redacted or omitted.
- Missing evidence pack returns a proper not-found state.
- Evidence from another workspace is not visible.
- Lists are paginated or bounded with deterministic ordering.

### Canonical Decision History

- Proposed, approved, rejected, and superseded decisions render.
- Status filters work.
- Detail pages show scope, actor, timestamps, evidence refs, and supersession
  chain.
- Approval/rejection/edit actions are tested only if implemented in this phase.
- Decisions from another workspace are not visible.
- Lists are paginated or bounded with deterministic ordering.

### Conflict and Ambiguity List

- Unresolved conflicts render from real conflict/evidence data.
- Filters by provider, scope, type, and severity work.
- Conflict rows link to evidence and decision detail pages.
- Empty state does not imply all context is safe unless supporting data exists.
- Conflicts from another workspace are not visible.
- Lists are paginated or bounded with deterministic ordering.

### Connector Setup and Source Selection

- Implemented providers show connection and source selection state.
- Source selection changes require admin authorization.
- Provider tokens and secrets never render.
- Reauthorization and provider error states are visible.
- Connector state from another workspace is not visible.

### Backfill and Replay Status

- Running, queued, completed, failed, skipped, and deadletter states render.
- Replay/re-sync/re-index actions create audit records.
- Long-running actions return job IDs instead of blocking.
- Failure reasons are useful and redacted.
- Job state from another workspace is not visible.
- Lists are paginated or bounded with deterministic ordering.

### Visual Quality

- Core pages render without overlap at desktop and mobile widths.
- Long URLs, source names, provider errors, and IDs wrap cleanly.
- Tables remain scannable with representative data volume.
- Empty/error/denied states are visible and specific.

### Accessibility

- Core navigation and actions are keyboard reachable.
- Focus states are visible.
- Pages expose useful landmarks.
- Form controls and action buttons have labels.
- Status is not communicated by color alone.
- Text and status indicators meet basic contrast expectations.

## Playwright Smoke Flow

Minimum required browser flow:

1. Log in or establish the configured internal admin session.
2. Seed the deterministic persistent UI test workspace.
3. Open source health.
4. Confirm at least one real source row appears from store data.
5. Open a source detail page.
6. Trigger or inspect a backfill/re-sync job if a safe fixture/staging target is
   available.
7. Open evidence-pack list.
8. Open an evidence-pack detail page.
9. Confirm gate status, cited sources, and source coverage render.
10. Confirm no raw private content appears for disallowed evidence.
11. Log in as or simulate a non-admin actor and confirm a sensitive action is
    denied and audited.

## Suggested Commands

```bash
ruff check src tests
mypy src
pytest tests/api/test_ui_guard.py tests/ui
pytest tests/e2e/test_minimal_ui_smoke.py
```

If the UI uses browser-only behavior, run Playwright in both desktop and mobile
viewports and save screenshots for closeout.

## Manual Visual Review

Review these pages at desktop and mobile widths:

- source health list and detail,
- evidence-pack list and detail,
- canonical decision list and detail,
- conflict list,
- connector setup/source selection,
- backfill/replay status.

Check:

- no overlapping text,
- no clipped buttons,
- no secret/token display,
- clear empty/error/denied states,
- timestamps and IDs are copyable,
- sensitive actions require confirmation.

## Exit Evidence

Record under this phase directory:

- test command summaries,
- Playwright screenshots or screenshot paths,
- manual review notes,
- any pages intentionally deferred,
- known permission/redaction gaps.
