# Phase 19 Engineering Review

## Status

Approved if Phase 14 services remain the data source.

## Required Guardrails

- No duplicate business logic in templates or client code.
- No static replacement for real service state.
- All mutating actions reuse shared action contract.
- Pages are paginated or bounded.
- UI never renders provider secrets or raw private content by default.

## Failure Modes To Test

- Polished page silently uses fake data.
- Client-side route bypasses server permission check.
- Toast says success while background job failed.
- Long errors or source names overlap controls.
- Role-denied state leaks target metadata.

## Review Checklist

- [ ] Thin routes.
- [ ] Real read models.
- [ ] Shared action contract.
- [ ] Browser tests for happy and denied paths.
- [ ] Accessibility pass recorded.
