# Phase 12 Engineering Review

## Review Verdict

Status: approved with corrections folded into the plan.

Scope challenge result: proceed as runtime packaging. Do not expand into
Kubernetes, autoscaling, full backup/restore, or Phase 13 platform components.

## What Already Exists

| Sub-problem | Existing code/docs | Reuse verdict |
| --- | --- | --- |
| FastAPI app | Earlier phases | Containerize as API service. |
| Worker entrypoints | Earlier worker phases | Run independently by role. |
| Postgres/Alembic | Phase 0+ | Use for Compose migration smoke. |
| Kafka runtime | ADR-022 | Use Apache Kafka KRaft in Compose. |
| Observability | Phase 11 | Expose config, do not require Grafana keys locally. |
| Health/readiness | Phase 0/11 | Harden for runtime dependencies. |
| Service boundaries | ADR-019 | Document Kubernetes-compatible shape. |

## NOT In Scope

- Kubernetes manifests.
- Production autoscaling.
- Full backup/restore implementation.
- Public admin UI.
- New connectors.
- New retrieval/security features.
- Phase 13 platform components.

## Architecture Review

1. [P1] (confidence: 9/10) `plan.md` - base Compose smoke must not require real
   Slack/Linear/GitHub/OpenAI/Grafana credentials. The plan requires
   deterministic/local defaults.

2. [P1] (confidence: 9/10) `plan.md` - health/readiness must fail clearly when
   dependencies are missing. Opaque container crashes are not acceptable.

3. [P1] (confidence: 8/10) `plan.md` - worker roles must be independently
   runnable so scaling boundaries are real, not just documented. The plan now
   distinguishes current `pipeline`/`noop` CLI roles from future role
   boundaries.

4. [P2] (confidence: 8/10) `plan.md` - Compose should use Apache Kafka KRaft to
   match ADR-022, not a Kafka-compatible substitute.

5. [P2] (confidence: 8/10) `plan.md` - Kubernetes compatibility should be docs
   and boundaries only. No manifests are needed.

6. [P2] (confidence: 7/10) `plan.md` - object storage should be included in
   Compose because raw payloads/files are part of the data boundary.

7. [P1] (confidence: 9/10) `plan.md` - migrations need an explicit
   command/service. API and workers should not auto-run migrations on normal
   startup.

8. [P2] (confidence: 8/10) `plan.md` - Compose needs service healthchecks where
   practical. `depends_on` alone does not prove dependencies are ready.

9. [P2] (confidence: 8/10) `plan.md` - reproducible image builds need a pinned
   dependency source and `.dockerignore`/build-context guardrails.

## Code Quality Review

1. [P2] (confidence: 8/10) Keep container entrypoints thin. Runtime behavior
   should stay in app/worker modules, not shell scripts.

2. [P2] (confidence: 8/10) Settings validation should be typed and testable.
   Avoid parsing deployment config ad hoc in entrypoints.

3. [P2] (confidence: 8/10) Health checks should report sanitized dependency
   names/statuses, not connection strings or secrets.

4. [P3] (confidence: 7/10) Use a smoke script that prints concise JSON/status so
   CI and humans can read failures.

5. [P3] (confidence: 7/10) Keep Compose service names aligned with the actual
   file, e.g. `minio` for object storage unless an alias is intentionally added.

## Test Review

Detected framework: Python, pytest, Docker Compose.

```txt
CODE PATHS                                      DEPLOYMENT FLOWS
[+] Container images                            [+] local Compose smoke
  ├── [★★ PLANNED] API image                      ├── [★★★ PLANNED] explicit migration
  └── [★★ PLANNED] worker image                   ├── [★★ PLANNED] API health
[+] Runtime config                                ├── [★★ PLANNED] worker heartbeat
  ├── [★★★ PLANNED] missing deps fail clearly     └── [★★ PLANNED] Kafka/Qdrant/storage smoke
  └── [★★ PLANNED] deterministic local defaults
[+] Service boundaries
  └── [★★ PLANNED] scaling docs

COVERAGE: 12/12 critical paths planned (100%) | GAPS: 0
QUALITY: ★★★:2 ★★:10 ★:0
```

## Performance Review

1. [P2] (confidence: 8/10) Worker containers should allow role-specific resource
   tuning later. Do not force all worker roles into one process.

2. [P2] (confidence: 7/10) Docker image build time matters for iteration. Use
   dependency-layer caching.

3. [P3] (confidence: 7/10) Compose defaults should avoid over-consuming local
   resources while still running real Kafka/Qdrant/Postgres.

## Failure Modes

| Codepath | Production failure | Planned handling | Gap |
| --- | --- | --- | --- |
| Config | Missing DB/Kafka env. | Settings/readiness failure with clear reason. | No gap. |
| Worker | Invalid role silently noops. | Invalid role startup test. | No gap. |
| Compose | Requires real provider credentials. | Deterministic/local defaults. | No gap. |
| Secrets | Secret baked into image/config example. | Secret-boundary tests. | No gap. |
| Kafka | Runtime differs from ADR. | Apache Kafka KRaft service. | No gap. |
| Scaling | Boundaries unclear. | Hosted/Kubernetes-compatible docs. | No gap. |
| Migration | API auto-migrates unexpectedly or schema missing. | Explicit migration command/service and readiness check. | No gap. |
| Compose health | Containers started but dependencies unusable. | Healthchecks and smoke tests. | No gap. |
| Build context | Local env/run logs copied into image. | `.dockerignore`/build-context tests. | No gap. |

Residual risk: simple hosted containers may have weaker autoscaling than
Kubernetes. This is accepted for design-partner beta and documented as a later
trigger.

## Parallelization Strategy

| Step | Modules touched | Depends on |
| --- | --- | --- |
| Container builds | Dockerfiles/build config | existing entrypoints |
| Runtime entrypoints | API/worker command config | container builds |
| Settings | config/tests | entrypoints |
| Health/readiness | API/workers/tests | settings |
| Compose | compose/env files | settings + images |
| Smoke tests | scripts/tests/deployment | Compose |
| Docs | deployment docs | service boundaries |

Parallel lanes:

- Lane A: images and entrypoints.
- Lane B: settings validation.
- Lane C: health/readiness after settings.
- Lane D: Compose after images/settings.
- Lane E: docs after boundaries are fixed.

Conflict flags: settings and health checks are shared by API and workers. Lock
the settings schema before broad container changes.

## Commit Strategy

Use multiple commits:

1. `phase 12: add container build foundations`
2. `phase 12: add runtime entrypoints`
3. `phase 12: add deployment configuration`
4. `phase 12: add health and worker readiness`
5. `phase 12: add Docker Compose stack`
6. `phase 12: add deployment smoke tests`
7. `phase 12: document hosted container deployment`
8. `phase 12: document Kubernetes-compatible boundaries`

Each commit should include focused tests or validation artifacts for its slice.

## Completion Summary

- Scope Challenge: accepted as runtime packaging phase.
- Architecture Review: 9 issues reviewed, corrections folded in.
- Code Quality Review: 5 issues reviewed.
- Test Review: 12 critical paths planned, 0 gaps.
- Performance Review: 3 issues found.
- NOT in scope: written.
- Failure modes: simple hosted container autoscaling residual risk noted.
- Parallelization: 5 lanes.
- Commit strategy: 8 reviewable commits.
