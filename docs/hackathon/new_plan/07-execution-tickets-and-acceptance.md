# Execution Tickets and Acceptance

## Dependency map

```text
GIP-001 ─┬─> GIP-002 ─> GIP-005 ─┬─> GIP-007 ─> GIP-008
         ├─> GIP-003 ─> GIP-006 ─┘
         └─> GIP-004

GIP-008 ─> GIP-009 ─> GIP-010 ─┬─> GIP-011
                                ├─> GIP-012 ─> GIP-013
                                └─> GIP-014

GIP-011 + GIP-013 + GIP-014 ─> GIP-015 ─> GIP-016

GIP-013 ─> GIP-017 ─> GIP-018
GIP-016 + GIP-018 ─> GIP-019 ─> GIP-020
```

## Workstream A — Corpus and adapters

### GIP-001 — Freeze the incident manifest

**Deliverable:** Versioned manifest containing 18 records, stable IDs, source
modes, timestamps, relationships, decisive/distractor labels, and expected
citations.

**Acceptance:**

- exactly six decisive and twelve distractor records;
- exactly six displayed source types;
- no real customer or credential data;
- stable content hashes across repeated loads.

### GIP-002 — Add the runnable Python incident service

**Deliverable:** Minimal session middleware and focused pytest representing the
Redis/Postgres fallback defect.

**Acceptance:**

- the initial focused test reproduces the failure;
- evidence references the actual module and test path;
- the demo never requires applying the fix.

### GIP-003 — Build provider snapshot payloads

**Deliverable:** Typed GitHub, Jira, Drive, email, and agent-checkpoint snapshot
payloads generated from the manifest.

**Acceptance:**

- each payload validates against a bounded provider or snapshot contract;
- `mode=imported_snapshot` survives normalization;
- citations use safe demo URLs or internal references.

### GIP-004 — Add the email snapshot adapter

**Deliverable:** Provider-neutral bounded email snapshot contract, import plan,
normalizer registration, source-aware chunk behavior, and tests.

**Acceptance:**

- no OAuth, IMAP, Gmail, or Outlook network client is introduced;
- sender/recipient fields are synthetic and bounded;
- HTML, attachments, and raw headers are not accepted in this slice.

### GIP-005 — Emit every snapshot through shared ingestion

**Deliverable:** Idempotent plan that converts the manifest into
`RawEventInput` records and submits them through the shared ingestion seam.

**Acceptance:**

- no direct inserts into source-object, chunk, embedding, or Qdrant stores;
- repeated seed produces no duplicate canonical objects;
- every record carries workspace, source connection, provider, mode, trace, and
  stable idempotency identity.

### GIP-006 — Materialize demo permissions

**Deliverable:** Operator-only creation of the exact demo source scopes and
actor/provider principals.

**Acceptance:**

- caller-provided filters can narrow but never grant access;
- removed or cross-workspace sources are denied;
- no browser route creates permission scopes.

## Workstream C — Runtime and acceptance

### GIP-007 — Compose the durable demo runtime

**Deliverable:** Compose profile using Postgres, local Qdrant, API, worker, and
the existing event infrastructure.

**Acceptance:**

- readiness fails closed when migrations, scopes, embedding profile, or Qdrant
  schema are unavailable;
- Postgres remains canonical and Qdrant payloads remain content-free;
- restart preserves canonical state and searchability.

### GIP-008 — Build the idempotent preparation command

**Deliverable:** One operator command that preflights, seeds, drains/waits,
verifies counts, and writes a redacted run report.

**Acceptance:**

- human and JSON output modes;
- no credentials or source bodies in output;
- nonzero exit on any required gate;
- repeat run reports duplicates as no-ops.

### GIP-009 — Prove the pre-update golden query

**Deliverable:** REST and MCP task-context requests for the pre-Slack state.

**Acceptance:**

- prior agent checkpoint and five snapshot providers are available;
- diagnosis remains uncertain because the live confirmation is absent;
- evidence-pack ID and trace ID persist.

### GIP-010 — Inject the signed Slack transition

**Deliverable:** Deterministic signed Slack event using the existing webhook
verification and selected-source path.

**Acceptance:**

- bad signature and unselected channel are rejected;
- valid delivery is acknowledged once and deduplicated on replay;
- the message reaches a verified Qdrant point through normal workers.

## Workstream B — Retrieval and graph

### GIP-011 — Add coverage-aware reranking

**Deliverable:** Bounded provider-diversity boost after normal lexical/vector/
relationship fusion.

**Acceptance:**

- maximum eight final evidence items;
- no hard provider quota;
- original raw paths and scores remain in provenance;
- irrelevant provider results never outrank clearly relevant evidence solely
  because of diversity.

### GIP-012 — Define `TaskEvidenceGraph`

**Deliverable:** Versioned graph node/edge contract containing safe mode,
freshness, citation, and supporting/conflicting state.

**Acceptance:**

- graph contains no raw payload, token, transcript, vector, or private URL;
- node IDs are stable for the same evidence pack;
- conflicts and freshness are explicit fields, not inferred by the browser.

### GIP-013 — Add the permission-filtered graph API

**Deliverable:** `GET /v1/demo/tasks/{task_ref}/graph` derived from authorized
evidence and relationships.

**Acceptance:**

- trusted transport supplies workspace and actor authority;
- cross-workspace and missing-scope requests reveal nothing;
- the second graph contains the new Slack node and edge.

### GIP-014 — Add the golden evidence evaluator

**Deliverable:** Machine-readable assertions for decisive citations, provider
coverage, freshness ordering, conflict state, and the named file/test.

**Acceptance:**

- evaluates evidence semantics rather than exact Claude wording;
- fails if distractors displace a decisive item;
- fails if the stale doc appears without a conflict signal;
- records the exact expected and observed evidence IDs.

## Central integration

### GIP-015 — Prove the post-update golden query

**Deliverable:** Second REST and MCP request after the Slack event.

**Acceptance:**

- includes the new Slack evidence;
- exposes six-source coverage within eight items;
- freshness state is newer than the first pack;
- evidence supports the likely Redis fallback diagnosis and safe next action.

### GIP-016 — Run failure and restart matrix

**Deliverable:** Focused integration matrix.

**Cases:**

- duplicate snapshot seed;
- duplicate Slack delivery;
- Qdrant unavailable;
- worker/API restart;
- missing, removed, or stale scope;
- cross-workspace query;
- incompatible embedding/index profile;
- malformed graph projection.

**Acceptance:** every case is denied, partial, retryable, or recovered exactly
as declared; none silently falls back to global fixtures.

## Follow-on workstreams

### GIP-017 — Implement `/ui/demo`

Build source cards, mode badges, graph polling, SVG graph, and citation drawer
against the accepted graph contract.

### GIP-018 — Capture frontend proof

Run accessibility and browser checks, then capture source-card, pre-update,
live-node, and citation states.

### GIP-019 — Generate assets and pitch

Generate the four-slide deck, 20-second intro, narration, captions, screenshots,
and recovery clips from verified artifacts.

### GIP-020 — Freeze the demo release

Run the credentialed hosted-Qdrant/Slack gate, verify public claims, perform two
sub-three-minute rehearsals, checksum artifacts, and tag the accepted commit.

## Required validation commands

The implementation may add more focused commands, but the finish line includes:

```bash
ruff check .
ruff format --check .
mypy src
pytest tests/connectors tests/normalization tests/retrieval tests/api
docker compose config
python scripts/prepare_cortex_demo.py --mode compose --format json
```

Frontend and asset follow-ons add:

```bash
cd frontend
npm run lint
npm run typecheck
npm run build
```

## Review gates

1. **Corpus gate:** manifest and fixture reviewed before adapter implementation.
2. **Contract gate:** raw-event, graph, and evaluator contracts approved before
   parallel implementation reaches shared files.
3. **Compose gate:** all backend tickets pass locally before hosted credentials
   are introduced.
4. **Truth gate:** every displayed provider has an accurate source-mode label.
5. **Artifact gate:** screenshots, slides, and video are generated only from an
   accepted run or visibly labelled recovery footage.
