# Phase 11 Engineering Review

## Review Verdict

Status: approved with corrections folded into the plan.

Scope challenge result: proceed, but keep it lean. Phase 11 should deliver
operability for beta, not a full SRE platform or public admin console.

## What Already Exists

| Sub-problem | Existing code/docs | Reuse verdict |
| --- | --- | --- |
| Trace IDs and envelopes | pipeline envelope docs, earlier phases | Reuse for propagation. |
| Connector health | Phases 8 and 9 | Standardize metrics/logging. |
| Permission/redaction | Phase 10 | Must be applied before observability emission. |
| Retry/deadletters | connector/worker plans, ADR-015 | Surface and repair. |
| Retrieval/gate records | Phases 5 and 6 | Instrument latency, errors, counts. |
| Audit/admin auth | Phase 10 | Required for operations actions. |
| Grafana Cloud choice | ADR-018 | Use managed dashboards/alerts. |

## NOT In Scope

- Public admin console.
- Self-hosted observability stack.
- Kubernetes autoscaling/manifests.
- New connectors.
- Full deletion/retention workflow.
- Phase 12 runtime packaging.

## Architecture Review

1. [P1] (confidence: 9/10) `plan.md` - observability must not weaken Phase 10
   privacy. The plan requires redaction before logs/traces/metrics/dashboards.

2. [P1] (confidence: 9/10) `plan.md` - repair operations must reuse admin
   authorization and audit logging.

3. [P2] (confidence: 8/10) `plan.md` - metric labels need a safe low-cardinality
   allowlist to avoid cost/cardinality blowups and hidden-source leaks.

4. [P2] (confidence: 8/10) `plan.md` - dashboards should be tested against
   metric definitions. Otherwise dashboards rot quickly.

5. [P2] (confidence: 8/10) `plan.md` - every alert needs a runbook and
   simulation. No action, no alert.

6. [P3] (confidence: 7/10) `plan.md` - local no-op defaults are important so
   development does not require Grafana Cloud credentials.

## Code Quality Review

1. [P2] (confidence: 8/10) Put trace/log/metric helpers behind a small
   observability module. Do not hand-roll labels in every service.

2. [P2] (confidence: 8/10) Keep operations output schemas separate from raw DB
   records so redaction is explicit.

3. [P2] (confidence: 8/10) Alert definitions should live as versioned config or
   generated artifacts, not dashboard-only manual state.

4. [P3] (confidence: 7/10) Runbook links should be stable relative docs paths
   so alert annotations do not break after refactors.

## Test Review

Detected framework: Python, pytest, pytest-asyncio.

```txt
CODE PATHS                                      OPS FLOWS
[+] Trace propagation                           [+] connector failure
  ├── [★★★ PLANNED] API -> event -> worker        ├── [★★ PLANNED] dashboard
  └── [★★ PLANNED] retrieval/gate                 └── [★★ PLANNED] runbook
[+] Logs/metrics
  ├── [★★★ PLANNED] redaction
  ├── [★★ PLANNED] low-cardinality labels
  └── [★★ PLANNED] local exporter/no-op
[+] Alerts/dashboards
  ├── [★★ PLANNED] panel metric validation
  └── [★★ PLANNED] simulations
[+] Operations
  ├── [★★★ PLANNED] admin authorization
  └── [★★ PLANNED] audit records

COVERAGE: 10/10 critical paths planned (100%) | GAPS: 0
QUALITY: ★★★:3 ★★:7 ★:0
```

## Performance Review

1. [P2] (confidence: 8/10) Instrumentation must avoid hot-path DB round trips
   for labels/context.

2. [P2] (confidence: 8/10) Metrics should aggregate counts/statuses rather than
   emit one series per source object, chunk, repo, issue, or file.

3. [P2] (confidence: 7/10) Trace sampling should be configurable before beta
   traffic rises.

4. [P3] (confidence: 7/10) Alert simulations should be deterministic and not
   depend on live Grafana Cloud.

## Failure Modes

| Codepath | Production failure | Planned handling | Gap |
| --- | --- | --- | --- |
| Logging | Source snippet appears in logs. | Redaction tests and shared helpers. | No gap. |
| Metrics | High-cardinality hidden labels. | Label allowlist and tests. | No gap. |
| Tracing | Trace breaks across Kafka. | Producer/consumer propagation tests. | No gap. |
| Alerting | Noisy unactionable alerts. | Simulation and runbook requirement. | No gap. |
| Operations | Replay bypasses admin auth. | Phase 10 auth/audit required. | No gap. |
| Dashboards | Panels reference stale metrics. | Dashboard definition tests. | No gap. |

Residual risk: Grafana Cloud-specific provisioning details may vary by
environment. Keep dashboard/alert definitions versioned locally and validate
with local/static tests plus optional Grafana smoke.

## Parallelization Strategy

| Step | Modules touched | Depends on |
| --- | --- | --- |
| Foundations | `src/cortex/observability`, config/tests | Phase 10 redaction |
| Trace propagation | API, connectors, workers, retrieval/gate | foundations |
| Logs/redaction | API/connectors/workers/security tests | foundations |
| Metrics | services/workers/retrieval/gate | foundations |
| Dashboards | dashboard definitions/tests | metrics |
| Alerts | alert definitions/tests | metrics + runbook stubs |
| Operations | ops/admin endpoints/services | Phase 10 auth/audit |
| Runbooks | docs/runbooks | alerts/operations |

Parallel lanes:

- Lane A: foundations.
- Lane B: logs/redaction after foundations.
- Lane C: trace propagation after foundations.
- Lane D: metrics after foundations.
- Lane E: dashboards/alerts/runbooks after metrics.
- Lane F: operations/repair after Phase 10 auth integration.

Conflict flags: instrumentation touches many services. Keep helper APIs stable
before broad edits.

## Commit Strategy

Use multiple commits:

1. `phase 11: add observability foundations`
2. `phase 11: add trace propagation`
3. `phase 11: harden structured logs`
4. `phase 11: add operational metrics`
5. `phase 11: add Grafana dashboard definitions`
6. `phase 11: add beta alert rules`
7. `phase 11: add operations and repair surfaces`
8. `phase 11: document operations runbooks`

Each commit should include focused tests or validation artifacts for its slice.

## Completion Summary

- Scope Challenge: accepted as lean beta observability/ops phase.
- Architecture Review: 6 issues reviewed, corrections folded in.
- Code Quality Review: 4 issues reviewed.
- Test Review: 10 critical paths planned, 0 gaps.
- Performance Review: 4 issues found.
- NOT in scope: written.
- Failure modes: Grafana provisioning residual risk noted.
- Parallelization: 6 lanes after foundations.
- Commit strategy: 8 reviewable commits.
