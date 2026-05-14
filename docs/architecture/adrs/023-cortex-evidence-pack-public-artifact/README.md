# ADR-023: Cortex Evidence Pack Public Artifact

Status: Accepted

Date: 2026-05-14

## Context

Cortex needs a public proof artifact for recruiters, hiring managers, and
technical reviewers. A Loom or Miro board is not enough because those artifacts
are slow to scan and do not preserve the engineering tradeoffs behind the
system.

The strongest artifact is a public case study backed by evidence:

- a live case-study page,
- a short Loom showing the system working,
- an architecture diagram embedded in the page,
- screenshots and logs from local runs,
- focused tests and benchmark output,
- an ADR that explains the hard choices and the limits of the claim.

Current Cortex state supports an invite-only beta backend story with
production-shaped ingestion, retrieval, connector, tenant, billing, lifecycle,
and operations foundations. It does not yet support broad enterprise self-serve
or production-scale throughput claims.

## Decision

Build the Cortex public proof package around a "Cortex Evidence Pack" rather
than a standalone diagram board.

The primary artifact is the public case-study route:

```txt
GET /case-study
```

The route presents Cortex as:

```txt
Cortex: Evidence-Aware Knowledge Infrastructure for Engineering Teams
```

The case study shows the deterministic COR-123 demo path:

```txt
Slack + Linear + GitHub + repo docs
  -> ingestion API
  -> event envelopes / Kafka-compatible backbone
  -> workers
  -> Postgres source records
  -> chunks / OCR / embeddings / relationships
  -> cited retrieval
  -> allow/warn/block context gate
  -> evidence pack
```

Use the MCP-facing tool surface as a proof boundary, not as the product's main
story. The tools demonstrate that agents can call Cortex before acting:

- `retrieve_context`
- `get_related_work`
- `check_context_gate`
- `propose_canonical_decision`
- `approve_canonical_decision`

The product story is cited context and risk gating for engineering work. MCP is
the integration surface that makes it useful to agents.

## Tradeoffs

### Public Page Over Miro

Decision: make the live case-study page the primary artifact.

Why:

- recruiters skim pages before watching videos,
- pages are linkable from a resume,
- written claims can be tied directly to evidence,
- diagrams can be embedded instead of forcing viewers into another tool.

Cost:

- the page must stay current with actual repo behavior,
- diagrams and metrics need maintenance,
- fake polish is riskier than a plain but accurate proof page.

### Diagram In The Artifact

Decision: embed the architecture diagram in the case-study page.

Why:

- the architecture should be visible in the first skim,
- the viewer should not need a Miro account,
- the diagram can be versioned with code and docs.

Cost:

- hand-authored diagrams can drift,
- very detailed architecture is hard to fit on one screen,
- rendered HTML is less flexible than a dedicated diagramming tool.

Mitigation: keep the public diagram at system-boundary level and keep deeper
details in ADRs.

### Evidence Pack Over Product Tour

Decision: make evidence the center of the artifact.

Why:

- Cortex is an infrastructure system, not just a UI,
- the hard part is proving source context is cited and permission-aware,
- evidence makes resume claims auditable.

Cost:

- local demo evidence is not the same as production proof,
- screenshots and logs require redaction discipline,
- benchmark numbers must be measured before publication.

Mitigation: label local evidence clearly and avoid production-scale claims until
there is staging or production drill evidence.

### MCP Surface As Agent Boundary

Decision: describe MCP as the agent-facing surface for retrieval and gating.

Why:

- agents need a small set of tools, not database access,
- structured tool outputs are easier to test than chat responses,
- `check_context_gate` creates a clear pre-action control point.

Cost:

- MCP can distract from the deeper ingestion/retrieval architecture,
- local in-memory MCP tests are not proof of hosted connector readiness,
- every tool argument becomes part of a contract.

Mitigation: keep MCP language concise and point to the pipeline, evidence pack,
and gate result as the durable proof.

### allow/warn/block Over Auto-Action

Decision: gate risky work with explainable `allow`, `warn`, and `block`
statuses rather than automatically editing code or approving changes.

Why:

- risky engineering changes need human-readable reasons,
- a deterministic gate is easier to test and debug,
- blocked work can cite the exact stale, missing, or conflicting evidence.

Cost:

- false positives can slow agents down,
- blocked work needs a human resolution path,
- broad policy rules would create noisy gates.

Mitigation: keep v1 deterministic, narrow, and citation-required.

## Evidence To Capture

Before linking the case study from a resume or portfolio, capture a dated local
evidence folder with:

- case-study page screenshot,
- `/dev/workbench` timeline screenshot,
- retrieval inspector screenshot,
- context-gate `block` screenshot,
- evidence-pack JSON excerpt with redacted fixture-only source links,
- focused test output,
- benchmark output for retrieval and context-gate p50/p95,
- command log with commit hash.

Do not include:

- tokens,
- private URLs,
- raw customer payloads,
- unredacted provider object IDs from real workspaces,
- production claims that have not been drilled.

## Metrics Policy

Allowed now:

- fixture counts,
- source coverage,
- deterministic stage count,
- focused test count,
- eval accuracy for COR-123 local fixtures.

Publish only after measurement:

- retrieval p50/p95,
- context gate p50/p95,
- replay throughput,
- worker lag,
- production or staging availability.

Do not infer scale from local deterministic fixtures.

## What Breaks At 10x Scale

Hot sources:

- Slack and GitHub can produce bursty event patterns.
- Backpressure, cursor repair, retry policy, and fair scheduling become core.

Permission filtering:

- Live provider checks on every retrieval are too slow and brittle.
- ACL snapshots need freshness windows and fail-closed semantics.

Stale embeddings:

- Chunking, embedding, and ranking versions drift.
- Rebuilds need version-aware retrieval and clear index migration paths.

Worker backpressure:

- Replayable events help, but worker queues can still fall behind.
- Operators need lag metrics, dead-letter repair, and source-specific throttles.

Index rebuilds:

- Derived indexes should be disposable.
- Postgres source records must remain the durable rebuild source.

## Consequences

The case study becomes the resume-facing artifact, and this ADR explains the
tradeoffs behind it. The artifact should make Cortex look serious without
pretending local deterministic proof is the same as enterprise production proof.

The public claim should be:

```txt
Built a production-shaped FastAPI, Kafka-compatible, Postgres-backed knowledge
infrastructure system that ingests engineering context, returns cited evidence
packs, and gates risky changes with allow/warn/block decisions.
```

The public claim should not be:

```txt
Fully production-proven enterprise self-serve knowledge infrastructure.
```

That second claim needs hosted onboarding, live provider ACL drills, production
worker evidence, staging restore/rollback/load evidence, and measured latency.
