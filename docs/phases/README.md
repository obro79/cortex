# Cortex Phases

This directory is the working area for implementation phases.

- [`implementation-roadmap.md`](implementation-roadmap.md) is the ordered
  high-level roadmap.
- Each `phase-*` directory holds deeper planning and execution records for that
  phase.

Phase directories may contain:

- `README.md`: phase goal, scope, deliverables, validation, and links.
- `plan.md`: detailed implementation plan for the next build slice.
- `adrs/`: phase-local decisions that are too detailed for top-level ADRs.
- `postmortems/`: incidents, failed attempts, or rollback notes.
- `lessons/`: reusable findings from implementation.
- `evals/`: eval cases, results, and tuning notes.
- `run-logs/`: manual run notes and smoke-test evidence.

Keep top-level architecture decisions in [`../architecture/adrs/`](../architecture/adrs/).
Use phase-local ADRs for implementation choices scoped to one phase.

## Phase Index

- [Phase 0: Production Skeleton](phase-00-production-skeleton/)
- [Phase 1: Dev Workbench And Deterministic Fixtures](phase-01-dev-workbench-fixtures/)
- [Phase 2: Raw Event Pipeline](phase-02-raw-event-pipeline/)
- [Phase 3: Normalization And Source Objects](phase-03-normalization-source-objects/)
- [Phase 4: Chunking And Indexing Base](phase-04-chunking-indexing/)
- [Phase 5: Retrieval And Evidence Packs](phase-05-retrieval-evidence-packs/)
- [Phase 6: Context Gate](phase-06-context-gate/)
- [Phase 7: Human-Approved Canonical Memory](phase-07-canonical-memory/)
- [Phase 8: Real Slack Connector](phase-08-real-slack-connector/)
- [Phase 8.5: Slack Connector Review And Manual Testing](phase-08-5-slack-review-manual-testing/)
- [Phase 9: Linear + GitHub + Repo Docs](phase-09-linear-github-repo-docs/)
- [Phase 10: Permissions And Security](phase-10-permissions-security/)
- [Phase 11: Observability And Operations](phase-11-observability-operations/)
- [Phase 12: Runtime Deployment](phase-12-runtime-deployment/)
- [Phase 13: Layer-Later Platform Components](phase-13-layer-later-platform/)
- [Phase 14: Minimal Web UI](phase-14-minimal-web-ui/)
- [Phase 15: Self-Serve Product Foundation](phase-15-self-serve-product/)
- [Phase 16: Self-Serve Connector Setup](phase-16-self-serve-connectors/)
- [Phase 17: Billing And Plan Enforcement](phase-17-billing-plan-enforcement/)
- [Phase 18: Enterprise RBAC And Permission Hardening](phase-18-enterprise-rbac-permissions/)
- [Phase 19: Polished Customer Admin UI](phase-19-customer-admin-ui/)
- [Phase 20: Data Lifecycle, Compliance, And Trust](phase-20-data-lifecycle-compliance/)
- [Phase 21: Production Operations](phase-21-production-operations/)
- [Phase 22: Enterprise Readiness Gate](phase-22-enterprise-readiness/)
