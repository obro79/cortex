# Cortex Hackathon Architecture & Review Packet

**Status:** Draft v0.2 — full target architecture retained; local delivery profile separated
**Base repository:** Cortex, not CortexG
**Planning constraint:** 3–5 days for the first proof; target architecture intentionally untrimmed; local control-plane UI planned separately and starts only after a safe frontend checkpoint
**Execution breakdown:** [100-ticket backlog](100-ticket-execution-backlog.md)

## 1. Product decision

Cortex is a **company-context MCP**, not a new chat product.

Sources flow into Cortex. Cortex normalizes, indexes, governs, and cites them. Small evidence packs flow out to Claude Code, Codex, Cursor, or another existing agent. A future dashboard is a control plane for sources, index health, permissions, and evidence—not a competing assistant.

The demo claim should be:

> Ask what the company already knows, including what a teammate’s approved Claude Code session learned. Get a cited handoff, then fork the work with the teammate’s permission.

It must not claim access to arbitrary private Claude chats or the ability to resume another person’s session from an ID alone.

## 2. Scope and non-goals

### Scope policy

The destination architecture is intentionally **not** reduced to fit the first demo. Postgres, object storage, Kafka, hybrid FTS/vector retrieval, media extraction, multiple sources, and the MCP control plane remain in the target. P0/P1 labels below describe build order and what may be claimed in the first recording; they do not delete product scope.

### Hackathon scope

- One real Slack backfill plus one controlled live Slack event through one queryable Cortex runtime.
- A deterministic GitHub snapshot importer and one explicit, redacted Claude Code handoff in the same cited corpus.
- Optional sanitized Google Workspace or Atlassian material only as an import bundle with clear provenance—not as a claimed OAuth connector.
- Cited retrieval through a real MCP transport, demonstrated in Claude Code and validated with an MCP protocol/Inspector smoke test.
- A truthful ingest/index ledger that reports real events, objects, chunks, failures, and timing.
- Hybrid retrieval: source/permission filtering plus Postgres full-text and Qdrant vector candidates, fused into cited evidence.
- Object storage for raw provider payloads, original files/media, and versioned OCR/transcript/caption artifacts.

### P0 acceptance path

~~~text
Slack backfill + live message
        + GitHub snapshot + approved Claude handoff
        → one shared Cortex runtime
        → retrieve cited cross-source evidence in Claude Code
        → generate an actionable, opt-in continuation handoff
~~~

This is the critical proof path before packaging. Google Workspace, Jira/Confluence, media extraction, a second live connector, and a broader UI remain part of the destination and can run in parallel once the shared data path is stable.

### Explicit non-goals for this sprint

- Rebuilding or deleting the current UI before its user-owned scaffold has a safe checkpoint and the first API vertical slice exists.
- Claiming live media understanding without an actual OCR or transcription result.
- Building every provider’s OAuth and webhook integration before the core retrieval path works.
- Porting CortexG code wholesale. Its event and normalization ideas are useful; its current worktree is too stale and dirty to treat as a source of drop-in code.
- Production-grade multi-tenant deployment, device-login UX, or a full Kafka/Qdrant rollout during the demo sprint.

## 3. Current-state review

| Finding | Evidence in Cortex | Consequence |
| --- | --- | --- |
| Durable ingestion foundation exists | Raw events, SQL persistence, Kafka envelope/consumer, normalizers, chunking, embeddings | Keep this domain model and event vocabulary. |
| Slack is the strongest live connector | OAuth, channel selection, backfill, and webhook components exist | Make it the first real source. |
| GitHub has real client/connector foundations | Client and route-level connector code exist, but source/job/cursor state is not durable | Use it as a payload/client reference for a deterministic snapshot importer in this sprint. |
| The data plane is split today | Connector ingestion, worker stores, and MCP retrieval use different stores/runtime instances | The main P0 is one shared composition root. |
| The worker pipeline stops after embeddings | There is no completed embedding → index → retrieval handoff in the app path | Add the missing index stage before adding more sources. |
| MCP is an in-process prototype | Current server exports a function dispatcher over an empty in-memory retrieval service | Replace it with an actual MCP SDK stdio proxy/server backed by the shared runtime/API. |
| Retrieval architecture is planned but not wired | Existing ADRs choose Postgres FTS plus Qdrant, but live adapters are not in the app path | Implement target interfaces and explicit readiness; local adapters may support the first proof without changing the target. |
| Slack files are metadata-only today | No actual OCR/transcript retrieval path exists | Do not promise live image/video query until extracted text is present. |

The two architecture defects that block a credible demo are therefore not missing connectors; they are **split runtime state** and **the missing post-embedding index stage**.

### Full durable target architecture

The durable target keeps the complete hybrid design. FastAPI owns authenticated connector intake, retrieval, and control APIs; it composes clients to durable stores but is not an in-memory source of truth. Stateless workers consume Kafka and use the same Postgres/object-store contracts. The local HackathonRuntime is only a local execution profile for the first demo.

| Store or component | Authority and role | Rebuild rule |
| --- | --- | --- |
| Postgres | Canonical tenant/access state, connector state/cursors, raw-event metadata/object pointers, normalized objects/files, extracted text, chunks, relationships, embedding/index provenance, evidence, audit, and retention state | Restore before all derived stores. Its chunk text is the authoritative retrievable text. |
| Object storage | Immutable large bytes: raw provider payloads, originals for files/images/audio/video, and versioned OCR/transcript/caption/keyframe manifests | Restore with Postgres; object keys/hashes are referenced from Postgres. |
| Kafka | Durable transport, ordering, retry, and replay coordination for pipeline events | Not a primary content authority; replay from Postgres/object-storage truth when necessary. |
| Qdrant | Metadata-only semantic vector index; no source text, bytes, signed URLs, or provider secrets | Rebuild from canonical chunks and embedding records. |
| Postgres FTS | Lexical derived index over authorized canonical chunks | Rebuild from canonical chunks. |
| MCP proxy | Stateless stdio adapter for agent clients | Calls authenticated Cortex APIs; owns no content or index state. |

~~~mermaid
flowchart LR
  subgraph Sources
    S[Slack / GitHub / Drive / Atlassian]
    H[Approved Claude handoff]
    F[Files, images, audio, video]
  end
  S & H --> I[Provider adapter → RawEventInput]
  F --> MF[Provider-ID fetch]
  I --> PG[(Postgres metadata + canonical records)]
  MF --> OS[(Object storage: original bytes + manifests)]
  OS --> EX[OCR / transcript / caption / keyframe extraction]
  EX --> PG
  PG --> CH[Canonical chunks]
  CH --> FTS[Postgres FTS index job]
  CH --> EMB[Embedding job]
  EMB --> QD[Qdrant vector index job]
  FTS & QD --> READY[IndexReadiness projection]
  READY --> RET[Concurrent lexical + semantic retrieval]
  RET --> API[Authenticated Cortex API]
  API --> MCP[Stateless stdio MCP proxy]
  MCP --> AG[Claude Code / Codex / Cursor]
  I --> K[Kafka event transport]
  K --> EX & CH & EMB & FTS & QD
~~~

### Media lifecycle and provenance

Large media never travels as bytes in Kafka or as content in Qdrant payloads. A connector fetches by provider file ID using its credential; Cortex does not persist private provider download URLs as the retrieval mechanism.

~~~text
file.discovered → file.fetch_requested → file.fetched → media.validated
→ extraction.requested → extraction.completed → source_file.updated
→ chunks.upserted → embeddings.completed
→ Postgres FTS indexed + Qdrant vector indexed → hybrid_ready
~~~

- Images: metadata, OCR, and optional visual caption/diagram extraction.
- PDFs: page text/OCR with page-level citations.
- Audio/video: timestamped transcript segments plus sampled/keyframe OCR or captions with timecodes.
- Extraction artifacts are versioned in object storage and normalize into Postgres chunks with source-file ID, model/version, page/time/frame span, stable source reference, and content hash.
- Media/Extraction states include discovered, fetching, fetched, extracting, extracted, failed_retryable, failed_terminal, stale, and deleted. Deletion/revocation removes original bytes, derived artifacts, chunk/FTS visibility, Qdrant points, and cached evidence before retaining only non-content tombstones.

### Hybrid retrieval semantics

1. Authenticate the MCP proxy and derive workspace, actor, and allowed source/access snapshot server-side.
2. Plan the query and create one query embedding.
3. Run Postgres FTS and Qdrant candidate search concurrently with workspace, status, version, and access filters.
4. Fuse/deduplicate candidates by chunk ID, initially with reciprocal-rank fusion; permission-filter before text hydration and again after relationship expansion.
5. Hydrate allowed chunk text and citations from Postgres only, then optionally rerank and build a bounded evidence pack.
6. Return lexical/vector paths, source coverage, index versions, freshness, and explicit partial-result status. Hybrid_ready means every configured required target succeeded; the system never silently represents partial coverage as complete hybrid search.

## 4. Proposed architecture decision: one pipeline, two execution modes

**Recommendation: accept this as ADR-H1.**

Keep Cortex’s existing durable architecture as the destination, but make the hackathon path a thin, inspectable HackathonRuntime behind a feature flag. It is a local execution profile over the same source contracts, object-storage boundary, event vocabulary, and retrieval interfaces—not a parallel mock pipeline or a replacement for the durable target.

1. **Local HackathonRuntime:** one runtime is composed once inside the local Cortex API process. Live connector input, imported snapshots, the pipeline runner, retrieval, and ledger use that same runtime. It uses a local object-store-compatible adapter plus a file/SQL journal before making any persistence claim. It may run Postgres FTS and local Qdrant; if a configured retriever is unavailable, status reports lexical_ready/vector_ready/hybrid_ready explicitly.
2. **Durable target:** FastAPI owns intake, retrieval, and control APIs; stateless Kafka workers drive the same source events and stage handlers over Postgres, object storage, and Qdrant. This remains aligned with Cortex ADR-002, ADR-004, ADR-005, and ADR-010.

The rule is: **two transports, one logical data flow.** Do not create separate normalization, chunking, or retrieval logic for demo versus durable modes.

~~~mermaid
flowchart LR
    subgraph Sources
      S[Slack — live]
      G[GitHub — backfill/import]
      W[Google Workspace — snapshot first]
      A[Atlassian — snapshot first]
      C[Claude Code handoff — opt in]
      M[Images / video — extracted text only]
    end

    S & G & W & A & C --> I[Source adapter / raw event]
    M --> OStore[Object storage + extraction manifest]
    I --> L[Raw-event + ingest ledger]
    L --> N[Normalizer]
    N --> O[Source object/file + access snapshot]
    O --> K[Source-aware chunks]
    K --> FTS[Postgres FTS index job]
    K --> E[Embedding job]
    E --> V[Qdrant vector index job]
    FTS & V --> X[IndexReadiness]
    X --> R[Hybrid cited retrieval + evidence packs]
    R --> H[Local Cortex API]
    H --> P[Stateless stdio MCP proxy]
    P --> CC[Claude Code]
    L --> D[Later dashboard / health API]
~~~

### Required composition root

The demo path needs one HackathonRuntime (the exact name can change) that owns:

- source connection and sync state;
- raw-event and ingest-ledger repositories;
- object storage/payload-store adapter and extraction-job registry;
- normalizer registry and source-aware chunker;
- embedding provider, Postgres FTS, Qdrant/vector adapter, and index-readiness projection;
- retrieval service, evidence repository, canonical-memory and context-gate services;
- pipeline event transport and stage handler registry.

The demo API route receives this runtime through dependency injection or a narrow service API. It must not create a seeded/in-memory retrieval service. Do not refactor unrelated durable connectors or platform state during this sprint.

### ADR-H1a: MCP topology

In the local profile, FastAPI owns the only HackathonRuntime. The cortex-mcp process is a stateless stdio proxy that calls a narrow authenticated local Cortex API over loopback HTTP or a Unix socket. It never constructs repositories, a retrieval service, or seeded data. In durable mode, FastAPI owns the authenticated control/retrieval API and workers own no in-memory source of truth.

MCP tools do not accept workspace or user identity. The proxy presents a short-lived local demo credential; the API derives the fixed demo workspace and actor from it. A cortex://evidence/{id} resource is optional for the sprint; P0 is cited, bounded evidence returned from the same API path.

### Event lifecycle

Keep the current first stages and finish the chain:

~~~text
source input
  → raw_event.persisted
  → source_object.upserted
  → source_file.fetched / extraction.completed when applicable
  → source_chunk.upserted
  → postgres_fts.indexed → lexical_ready
  → embedding.requested
  → embedding.completed
  → qdrant.indexed → vector_ready
  → hybrid_ready when configured lexical and vector targets are both current
~~~

Every stage is idempotent on workspace, provider, source object key, version, and stage. The ledger records the event ID, trace ID, source reference, input/output counts, timing, retry count, and terminal status. This gives the demo its real “we indexed N events” evidence without invented counters.

Webhook path: verify → persist idempotently → enqueue → acknowledge. The pipeline runs after acknowledgment. Backfill checkpoints after each provider page, not only at completion. Job states are queued, running, retrying, failed, and completed; every nonterminal job has a retry/replay action and visible last error. Lexical_ready means FTS can return a chunk; hybrid_ready means every configured required target can return it.

### Reproducible demo bootstrap

Before coding, define a versioned demo manifest, proposed as demo/manifest.json. A cortex-demo bootstrap command must deterministically rebuild source connections, source objects, files, object-storage artifacts, chunks, FTS/vector projections, and baseline ledger from that manifest on a fresh startup. Live Slack events may then replay through the same path. Local persistence is explicit: use a file/SQL replay journal plus an object-store-compatible local adapter, or label the run ephemeral; never call a memory-only run durable. Reproducible startup, stable counts, and golden evidence references are required.

## 5. Source adapter contract

There are two explicit boundaries. No provider-specific code writes directly to a vector index or evidence pack.

| Boundary | Responsibility | Required output |
| --- | --- | --- |
| ProviderAdapter | Authentication, discovery, backfill, webhook verification, cursor handling, and immutable provider-payload capture | RawEventInput with stable provider event/object IDs, plus cursor/import manifest and idempotency metadata |
| NormalizerRegistry | Provider payload → canonical source object, source file, relationships, deletion state, and access snapshot | Canonical domain records consumed by the shared chunk/index pipeline |

Snapshot importers use the same RawEventInput boundary plus a versioned import manifest. Repair is a shared concern: idempotency key, replay range, job status, and error reason belong in the ingestion ledger.

### Prioritized source plan

| Source | Priority and sprint treatment | Demo proof |
| --- | --- | --- |
| Slack | **P0:** live backfill plus one controlled live event | New message appears in ledger, becomes queryable, and is cited. |
| GitHub | **P0:** deterministic snapshot importer using the existing client/connector as a payload reference; real App OAuth, cursors, and webhooks are deferred | PR/issue/commit appears in the same evidence pack as Slack context. |
| Claude Code | **P0:** explicit user-approved import/hook artifact | A handoff summarizes decisions, commands, files, blockers, and citations. |
| Google Workspace | **Target connector:** snapshot importer first, then Drive/Docs OAuth and change cursor | Imported doc is linked and cited, with import-manifest provenance. |
| Jira / Confluence | **Target connector:** snapshot importer first, then Atlassian OAuth/webhooks | Ticket or decision page is retrievable and cited. |
| Images/video | **Target capability:** object-storage original + versioned OCR/transcript/caption extraction | The answer cites derived text with page/time/frame provenance and links to authorized media. |

This keeps the product visibly multi-source while keeping claim discipline: the recording labels each source as live, indexed snapshot, or extraction-ready based on its actual state. No target source is removed from the architecture.

## 6. Retrieval and evidence contract

The retrieval boundary should return an evidence pack, not a free-form answer generated by Cortex. An agent remains responsible for its own reasoning and response.

Target claim: **hybrid company context retrieval**. Postgres FTS handles exact identifiers, filenames, ticket IDs, and keyword filtering; Qdrant handles semantic/vector recall. The query planner applies workspace/source/status/access filters to both paths, fuses candidates, hydrates authorized text from Postgres, and emits cited evidence. A real embedding provider and paraphrase evaluation are required before making a semantic-quality claim.

Readiness is explicit: lexical_ready means FTS is current; vector_ready means the active embedding/vector version is current; hybrid_ready means both configured paths are current. A degraded query can return a visible partial-result flag, but cannot present itself as complete hybrid coverage.

Minimum MCP operations:

| Operation | Purpose |
| --- | --- |
| retrieve_context | Search the authorized corpus and return concise, cited evidence. |
| get_related_work | Expand a selected evidence pack through explicit links and shared objects. |
| get_handoff | Return an approved Claude session handoff with source provenance and safe continuation instructions. |
| check_context_gate | Existing optional safety signal before a consequential agent task. |
| list_sources or source_status | Expose connection and index freshness when an agent needs to explain coverage. |

The MCP response includes source title, provider, source URL or stable reference, timestamps, chunk/object IDs, retrieval request ID, and evidence-pack ID. Full documents are fetched only through an authorized evidence resource such as cortex://evidence/{id} when that resource is implemented; it is not required for the first demo.

Hackathon authorization is deliberately narrow: one fixed demo workspace and one MCP proxy identity bound by a short-lived local token/configuration. Tools do not accept workspace or user identity. All corpus sources are approved for that demo identity; per-user Slack, Drive, and Jira ACL enforcement is a durable-mode follow-up. Handoff sharing, expiry, and revocation remain in scope.

## 7. Claude Code handoff design

The session connector is a first-class source adapter, but it is deliberately opt-in.

1. A user explicitly selects or exports a Claude Code session/transcript.
2. The importer applies best-effort, defense-in-depth redaction for secrets, .env/key material, and excluded paths before raw persistence; the demo corpus is sanitized independently because transcript/tool output may still contain sensitive material.
3. It validates a versioned handoff-v1.json artifact containing version, owner, approved recipients, workspace, repo/branch/commit, redacted segments, citations, expires_at, revoked_at, and content hash.
4. It normalizes session metadata and segments: prompt, response, command, file touched, decision, blocker, outcome, and source references.
5. Cortex creates a handoff evidence pack with task goal/current status, decisions, blocker, files changed or relevant files, commands/tests and results, next exact command or prompt, and citations across the session, Slack, GitHub, and other sources.
6. A teammate can inspect the handoff and, when the shared transcript is restored where Claude Code expects it in a compatible project/cwd, run claude --resume session-id --fork-session. Cortex provides a handoff reference; it does not impersonate the original user or promise arbitrary remote resume. A shared Agent SDK SessionStore is the durable cross-host follow-up, not a hackathon dependency.

Each handoff is a snapshot from its last successful, explicitly approved sync—not a live co-owned session. The safest labels are **Generate continuation handoff** and **Fork from handoff**.

## 8. Security and data handling baseline

- Store provider credentials outside source records; never index tokens.
- Preserve source access snapshots and deletion state in the data model for durable mode; the hackathon enforces only demo-workspace isolation.
- Require explicit session sharing and enforce approved recipients, expiry, and revocation/deletion state.
- Apply best-effort redaction before persistence, indexing, and evidence rendering; never treat it as a substitute for explicit consent and sanitized demo data.
- Use workspace-scoped, content-addressed object keys; issue short-lived authorized reads rather than storing provider-private download URLs or signed URLs in retrieval records.
- Keep original media bytes, extracted text, filenames, private URLs, and vectors out of Kafka payloads and Qdrant payloads. Qdrant holds only filterable metadata and point IDs.
- Log tool use, source connection actions, import runs, and evidence-pack access.
- Make source deletion/revocation remove or tombstone derived chunks and index entries through the same event flow in durable mode; handoff revocation is exercised in the demo test suite.

For the hackathon, use an isolated/sanitized Slack workspace and demo repositories. That is both safer and easier to explain.

## 9. Review plan and gates

### Initial architecture review: findings already established

| ID | Severity | Finding | Required disposition before demo |
| --- | --- | --- | --- |
| AR-01 | P0 | Three disconnected data planes mean connector data cannot reliably reach MCP retrieval. | Introduce the shared app composition root; prove one end-to-end path. |
| AR-02 | P0 | Canonical chunks do not yet flow through explicit FTS/vector index jobs into a queryable readiness projection. | Implement and test lexical_ready, vector_ready, and hybrid_ready stages. |
| AR-03 | P0 | Current MCP module is not a real transport and reads an empty fixture service. | Implement MCP SDK transport backed by the shared runtime/API. |
| AR-04 | P1 | Current MCP accepts caller-supplied workspace identity. | Derive identity/authorization from proxy authentication. |
| AR-05 | P1 | Claude session import does not exist in Cortex. | Build only opt-in, redacted import plus handoff format. |
| AR-06 | P1 | Slack media is metadata-only. | Restrict media claims to actual extracted text. |
| AR-07 | P2 | Existing frontend worktree is uncommitted and unrelated to this plan. | Leave it untouched until the data/MCP path has passed review. |
| AR-08 | P1 | The existing Kafka Slack smoke script does not await channel selection, so it is not a release gate. | Repair or replace it with an app-composition test. |
| AR-09 | P0 | An in-memory runtime cannot be shared with a separate stdio process. | Use ADR-H1a: FastAPI owns runtime; stdio is a stateless authenticated proxy. |
| AR-10 | P1 | Restart behavior and auth scope were previously implicit. | Require manifest bootstrap, a fixed demo workspace, and explicit handoff expiry/revocation tests. |
| AR-11 | P1 | Current deterministic embeddings and in-memory vector index do not prove semantic retrieval. | Ship a real embedding/Qdrant path plus paraphrase evaluation before claiming hybrid semantic quality. |
| AR-12 | P1 | Object storage/media extraction is architected but lacks a production adapter, fetch worker, and media lifecycle. | Add provider-ID fetch, object-store payload adapter, extraction manifests, and page/time/frame provenance. |
| AR-13 | P1 | FastAPI-owned local runtime can be mistaken for durable state ownership. | Keep local profile distinct from API/control-plane plus stateless Kafka workers in target architecture. |

### Review checkpoints

| Gate | When | Review question | Exit evidence |
| --- | --- | --- | --- |
| R1 — Architecture | Before implementation | Is there one API-owned runtime and a stateless cross-process MCP boundary? | Diagram, runtime boundary, event contract, file-touch plan approved. |
| R2 — Data and reliability | After pipeline wiring | Are backfill, retry, duplicate delivery, lexical/vector readiness, and media status truthful? | Idempotency/replay tests; real ledger trace for Slack, GitHub snapshot, and index readiness. |
| R3 — Security/privacy | Before real credentials or session import | Is demo-workspace isolation enforced and is handoff sharing safe? | Token/workspace test, redaction test, expiry/revocation behavior. |
| R4 — MCP interoperability | After MCP implementation | Does Claude Code get cited evidence from live/indexed data through a separate standard-MCP process? | Cross-process Slack → stdio proxy → cited retrieval test, MCP Inspector/protocol smoke test, invalid-token test. |
| R5 — Retrieval quality | Before recording demo | Does the evidence pack return exact identifiers and trustworthy hybrid cross-source context? | Golden lexical/vector/cross-source/no-result queries; fusion, freshness, and partial-result assertions. |
| R6 — Demo truthfulness | Before slides/video | Does every visible metric and capability have a captured trace? | Demo runbook, ledger screenshots/recording, claim checklist. |

### Minimum automated test matrix

- A clean bootstrap from the versioned manifest recreates the same source/chunk counts and selected golden evidence references.
- A Slack backfill and a GitHub snapshot importer produce queryable source objects in the same runtime.
- A controlled new Slack message moves through every stage to lexical_ready and hybrid_ready when vector is configured; GitHub live delivery is independently labeled by its actual state.
- Replaying the same provider event during processing creates no duplicate source object/chunk/index row.
- A delayed index, provider exception, and page-checkpoint restart are visible in the ledger and can be repaired/replayed.
- Retrieval returns source citations and enforces demo-workspace isolation and handoff sharing state.
- An invalid MCP token cannot obtain evidence; no tool can select a workspace by passing an ID.
- A Claude handoff import rejects malformed/expired/revoked artifacts, redacts test secrets, and requires explicit share authorization.
- Golden fixtures cover lexical, semantic/paraphrase, cross-source, and no-result queries; hybrid fusion and degraded partial-result behavior are asserted.
- A real image/PDF or video/audio sample completes provider-ID fetch, object-storage write, extraction manifest, page/time/frame chunking, and cited retrieval before media is demonstrated.
- No Kafka/Qdrant payload contains media bytes, raw extracted text, private URLs, filenames, secrets, or vectors beyond the permitted metadata boundary.
- The demo’s displayed counts equal ledger/database counts, not fixture constants.

## 10. Implementation order

### Day 1 — make the real path singular

1. Define the FastAPI-owned HackathonRuntime and a narrow local retrieval/evidence API protected by the demo proxy credential.
2. Stand up the object-store-compatible payload path, Postgres FTS job, Qdrant vector job, and IndexReadiness projection under the same contracts.
3. Add the ingest/index ledger plus the versioned bootstrap manifest and CLI/API status view.
4. Prove seeded/imported corpus → local API → evidence pack; no MCP implementation yet.

### Day 2 — prove Slack live plus GitHub context

1. Wire Slack backfill and one live webhook/update to the shared runtime.
2. Build a deterministic GitHub snapshot importer to the same RawEventInput boundary; defer GitHub App OAuth, durable cursors, and live webhooks.
3. Add replay/idempotency tests and capture source-count evidence.

### Day 3 — make it agent-native

1. Implement a real stateless stdio MCP proxy using the MCP SDK.
2. Route tool calls to the authenticated local Cortex API; prove the cross-process Slack → proxy → cited-retrieval path.
3. Add the opt-in redacted Claude session importer, handoff-v1.json validation, and get_handoff operation.
4. Run the first Claude Code end-to-end demo.

### Day 4 — make the demo defensible

1. Build a small set of golden hybrid cross-source queries, media cases, and failure cases.
2. Run R2–R5 reviews; fix only P0/P1 findings.
3. Capture ingest ledger, citations, and continuation-handoff evidence.
4. Run Google Workspace and Atlassian snapshot import tracks in parallel when they do not block the shared runtime; retain their OAuth/change-cursor work as the next connector milestone.

### Day 5 — package, not rebuild

1. Freeze a sanitized demo dataset and runbook, with deterministic replay as the primary path and a recorded live-sync fallback.
2. If R5 is complete early, create exactly one Cortex Handoff surface: source timeline, cited evidence, continuation handoff, and copy/open-in-Claude action. It is not a dashboard rebuild.
3. Record the demo and gather screenshots from real traces.
4. Write README, pitch, and slides from claims that passed R6.

## 11. Durable decision log

| Decision | Proposed answer | Status |
| --- | --- | --- |
| Product shape | MCP-first company context; no Cortex chat UI | Confirmed by product direction |
| Base codebase | Cortex, with selected CortexG ideas used only conceptually | Confirmed |
| UI | Postponed; do not delete existing work | Confirmed |
| Live source claim | Slack only; GitHub is backfilled/imported until live delivery is independently proven | Proposed, based on current connector readiness |
| Other sources | Google Workspace + Jira/Confluence as snapshot importers before full OAuth | Proposed |
| Claude workflow | Opt-in handoff/query/fork with no private-session claim | Confirmed product constraint |
| Pipeline | Local HackathonRuntime profile now; durable FastAPI/control APIs plus stateless Kafka workers over Postgres/object storage later | Confirmed architecture direction |
| MCP topology | FastAPI owns runtime; stdio is a stateless local proxy using a scoped demo credential | Proposed ADR-H1a |
| Storage | Postgres canonical metadata/text; object storage canonical large bytes/artifacts; Kafka transport; Qdrant derived vectors | Confirmed target architecture |
| Retrieval | Hybrid Postgres FTS + Qdrant with server-side filters, fusion, readiness/freshness, and partial-result signaling | Confirmed target architecture |

## 12. Confirmed architecture direction

**ADR-H1:** use a local HackathonRuntime delivery profile while preserving the full durable Postgres/object-storage/Kafka/Qdrant architecture behind the same contracts.

This preserves the full product architecture while giving the first implementation an inspectable, reproducible local profile. The build sequence determines what is demonstrable on a given day; it does not redefine Cortex’s destination.
