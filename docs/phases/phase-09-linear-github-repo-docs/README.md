# Phase 9: Linear + GitHub + Repo Docs

Phase source of truth: [`../implementation-roadmap.md`](../implementation-roadmap.md#phase-9-linear--github--repo-docs)

Artifacts:

- [`plan.md`](plan.md)
- [`implementation-checklist.md`](implementation-checklist.md)
- [`test-plan.md`](test-plan.md)
- [`autoplan-review.md`](autoplan-review.md)
- [`plan-eng-review.md`](plan-eng-review.md)

Goal: connect task intent and implementation evidence to Slack decisions by
adding Linear, GitHub, repo-doc imports, and deterministic relationships through
the same raw-event, source-object, chunking, retrieval, and context-gate spine.

Current implementation note: provider-shaped Linear/GitHub/repo-doc ingestion,
mocked live API client tests, and the no-secret live-smoke harness are in place.
TODO: run real internal/dev Linear and GitHub API smokes after credentials and
GitHub installation-token setup are available locally. No customer data before
Phase 10 approval.
