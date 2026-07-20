# Cortex: Built, Reusable, and 100-Ticket Execution Backlog

**Status:** Planning baseline, not yet entered into an issue tracker
**Repository:** recovered isolated Cortex snapshot; the original desktop worktree remains untouched
**Architecture:** Full durable target retained: Postgres + object storage + Kafka + Postgres FTS + Qdrant + MCP proxy
**Important:** Existing frontend changes are user work. The local control-plane UI is now in planning scope, but implementation starts only after its owner creates a safe checkpoint/review boundary.

## Recovered swarm status — 2026-07-19

This snapshot is intentionally isolated from the user's dirty desktop
worktree. **Landed** means local implementation plus focused automated proof;
it does not authorize a credentialed, Docker-backed, or production claim.

| Backlog item | Progress | What landed / what remains |
| --- | --- | --- |
| CTX-021, 025, 027 | Landed local foundation | Transactional outbox, bounded retry, and dead-letter/reconciliation seams have focused tests. Durable ingestion still needs to enqueue the raw event and outbox row in one real transaction. |
| CTX-043, 046 | Landed snapshot foundation | Typed Google Drive and Jira page/import plans emit supplied snapshots through the shared ingestion seam. OAuth, live clients, source persistence, normalizers, and central wiring remain open. |
| CTX-071 | Landed local transport | `cortex-mcp` supports newline-delimited JSON-RPC stdio and tool discovery. It currently uses the local fixture/in-memory MCP service, not an authenticated durable proxy. |
| CTX-077, 080 | Landed safe demo slice | `create_handoff_bundle` creates a portable opt-in handoff and always reports `session_accessed: false`; native Claude resume/fork remains unsupported. |
| CTX-096–100 | Landed deterministic demo packet | Ten synthetic multi-source records, three media sidecars, rehearsal, proof page/screenshots, README, scoreboard, editable deck, and 72-second fixture-only video are included. No live source, index, or production-readiness assertion is made. |
| CTX-109 | Partial | README and demo materials are now explicit about fixture-only scope; the wider phase documentation and smoke scripts still need their own drift audit. |

The 10 explicit cleanup tickets (CTX-101–110) remain intentional. No
destructive cleanup happens until the replacement path has a passing
integration proof and the user's dirty frontend work is separately reviewed.

## How to read this

- **[R] Reuse/wire:** substantive code already exists; the ticket makes it part of the real app path.
- **[E] Extend:** a credible foundation exists, but behavior/data model must be completed.
- **[N] New:** the capability does not exist as an executable Cortex component today.
- A ticket is done only when it has a focused automated test plus a meaningful runtime proof where applicable.

The backlog deliberately keeps the destination architecture untrimmed. The first demo can sequence tickets, but it does not redefine Cortex as a smaller product.

## Executive answer: what is already built?

| Area | Reality today | Reuse value | Main gap to close |
| --- | --- | --- | --- |
| Domain contracts and SQL model | Strong. Tenant, source object/file/chunk, embedding, index/lifecycle, audit, and pipeline contracts exist. | High | Wire all pieces through one live runtime. |
| Raw ingestion and eventing | Strong foundation. Durable raw-event service, payload store abstraction, replay, Kafka envelope/bus/consumer, and tests exist. | High | Complete one app-level composition and post-embedding/index flow. |
| Normalization and chunking | Strong. Slack, GitHub, Linear, repo-docs normalizers and source-aware chunking exist. | High | Add missing source types and ensure every connector uses the same stores. |
| Slack | Most mature source: OAuth, selected channels, webhooks, backfill, cursor, health, and tests. | High | Shared runtime, real query path, media fetch/extraction. |
| GitHub | Real HTTP client, normalizer, routes, and setup foundation. | Medium | Durable installation/source/cursor state; shared runtime; reliable backfill/webhook. |
| Retrieval and evidence | Strong components: FTS/vector interfaces, ranking, permissions, evidence packs, relationship expansion, context gate. | High | Actual persistent FTS/Qdrant adapters and app/API wiring. |
| Embeddings/indexing | Gemini and deterministic providers, index job concepts, Qdrant lifecycle deletion exist. | Medium | Qdrant upsert/search adapter, index workers, readiness projection. |
| Object storage/media | Interfaces, File/InMemory payload stores, SourceFile/OCR fields, lifecycle/deletion concepts exist. | Medium | S3/MinIO adapter, secure fetcher, extraction workers, media provenance. |
| MCP | Tool semantics and tests exist. | Medium | Actual SDK transport, stdio proxy, auth, hosted/local API boundary. |
| Security/ops | Tenancy, RBAC, provider ACL, audit, rate limiting, lifecycle, Kafka/ops tests are substantial. | High | Apply them consistently through the new end-to-end path. |
| UI | A newer uncommitted frontend scaffold exists. | Preserve and checkpoint first | It is a visual foundation for the planned local control plane, not yet a live product surface. |

## Reuse inventory with exact anchors

### Strong foundations to wire, not rewrite

| Capability | Existing anchors | Reuse decision |
| --- | --- | --- |
| API/config/CLI | src/cortex/api/app.py, src/cortex/config.py, src/cortex/cli/main.py | Keep FastAPI/Pydantic/Typer entrypoints; add a composition root. |
| SQL domain state | src/cortex/db/models.py, src/cortex/contracts/entities.py, src/cortex/contracts/pipeline_events.py | Extend migrations/models only where media, index readiness, and handoff need fields. |
| Raw event ingestion | src/cortex/ingestion/durable.py, service.py, raw_events.py, replay.py, payloads.py | Reuse durable input/idempotency/replay concepts. |
| Kafka/events | src/cortex/events/kafka_admin.py, src/cortex/workers/kafka.py, src/cortex/workers/factory.py | Keep event envelope, partitioning, retry/DLQ discipline; finish downstream stages. |
| Normalization | src/cortex/normalization/registry.py, service.py, normalizers/slack.py, github.py, repo_docs.py | Add Drive/Jira/Confluence/agent-session normalizers rather than inventing a second data model. |
| Chunking | src/cortex/chunking/source_aware.py, service.py, repositories.py | Reuse source-aware chunking for messages, docs, OCR, and session segments. |
| Slack connector | src/cortex/connectors/slack/ | Keep OAuth, source selection, backfill, signed webhook verification, health, client. Inject shared services. |
| GitHub connector | src/cortex/connectors/github/ | Keep HTTP client/setup shape; make connection state/backfill durable. |
| Retrieval | src/cortex/retrieval/service.py, fts.py, vector.py, ranking.py, evidence.py, permissions.py | Keep query/evidence/ranking contracts; replace in-memory adapters with persistent ones. |
| Embeddings | src/cortex/embeddings/service.py, gemini.py, deterministic.py | Retain provider-neutral model/version discipline; add real production vector delivery. |
| Index/lifecycle | src/cortex/indexing/, src/cortex/lifecycle/ | Reuse index job/lifecycle concepts and Qdrant delete adapter. |
| Context products | src/cortex/context_gate/, src/cortex/canonical_memory/, src/cortex/relationships/ | Keep as later MCP capabilities; do not block basic retrieval. |
| Auth/security/ops | src/cortex/auth/, security/, permissions/, observability/, platform/ | Reuse tenancy, ACL, audit, rate-limit, tracing, metrics, lifecycle patterns. |

### Existing but not yet a real product path

| Area | Current limitation |
| --- | --- |
| App composition | Connector services, workers, and MCP currently create/use separate in-memory or SQL state paths. |
| Worker chain | The SQL dispatcher processes raw events through embedding, but does not complete persistent FTS/Qdrant indexing into retrieval. |
| Retrieval defaults | src/cortex/retrieval/defaults.py and MCP use deterministic/in-memory fixtures, not connector-ingested state. |
| MCP | src/cortex/mcp/server.py is an in-process dispatcher, not an MCP SDK stdio/HTTP server. |
| Vector | src/cortex/indexing/vector_memory.py is in-memory; it does not provide meaningful semantic search or persistent Qdrant execution. |
| Object storage | src/cortex/interfaces/storage.py is a useful contract, but there is no production object-store adapter; PayloadStore is separate and currently memory/file backed. |
| Media | Slack deliberately retains metadata only for files/links. There is no provider-ID fetch, OCR/transcription, extraction manifest, or media citation pipeline. |
| External sources | Google Workspace, Jira, and Confluence adapters do not exist. |
| Agent handoff | No agent-session source, importer, redaction pipeline, or actual handoff MCP operation exists. |
| Frontend | Current UI worktree is dirty/uncommitted; preserve it and connect only after data/MCP proof passes. |

### Audit facts that change implementation priority

- Durable ingestion writes database state before Kafka publication. There is no transactional outbox/reconciliation worker, so a crash can strand a persisted event without a downstream publish.
- Retry fields exist, but no delayed retry scheduler/backoff/replay workflow is implemented. Unsupported worker events can currently be returned as no-op and committed.
- SQL repositories and migrations exist, but the current SQL method named search_fts performs Python substring matching rather than PostgreSQL tsvector search.
- Qdrant is provisioned and lifecycle deletion knows how to delete a configured point, but no vector upsert/search adapter exists.
- The root README is stale; docs/current-state.md is materially closer to the implemented backend. Neither replaces app-composition proof.

## Execution rules

1. No connector writes directly to retrieval/indexes. Every source emits RawEventInput and runs through the same normalization/chunk/index pipeline.
2. Postgres is canonical for metadata, normalized text, chunks, access state, evidence, and audit; object storage is canonical for large bytes and extraction artifacts.
3. Kafka transports/replays work; it is not the only content authority. Qdrant is derived and rebuildable.
4. A query never silently reports hybrid completeness when only FTS or only vector is fresh.
5. Every ticket that changes a data boundary includes idempotency, deletion/revocation, and authorization implications.
6. The existing dirty frontend worktree is never reverted, moved, or deleted by this backlog.

## Ticket backlog — 100 build tickets + 10 explicit cleanup tickets

### Epic A — Architecture, contracts, and program control (CTX-001–010)

| ID | Type | Ticket | Reuse / completion target |
| --- | --- | --- |
| CTX-001 | R | Land architecture packet and ADR-H1/H1a in Cortex docs | Port the approved plan into docs/specs and docs/adr; link existing ADR-002/004/005/010. |
| CTX-002 | E | Define durable-target versus local-profile configuration contract | Extend config.py; document FastAPI/control-plane versus local HackathonRuntime behavior. |
| CTX-003 | E | Define ConnectorAdapter and RawEventEmitter protocols | Reuse connector/service patterns; prohibit connector-private retrieval stores. |
| CTX-004 | E | Define IndexReadiness domain model and statuses | Extend contracts/entities and SQL migration for lexical_ready, vector_ready, hybrid_ready, partial/failed. |
| CTX-005 | E | Define object-key, content-hash, and provenance conventions | Align SourceFile, PayloadStore, and storage interface with workspace-scoped content addressing. |
| CTX-006 | E | Publish event-topic and partition-key contract | Reuse pipeline_events and ADR-002; add media/index/handoff events. |
| CTX-007 | N | Define demo manifest schema and bootstrap contract | Create versioned import/fixture manifest for repeatable data and source counts. |
| CTX-008 | E | Create architecture conformance test suite | Assert prohibited cross-layer dependencies and required runtime composition. |
| CTX-009 | E | Create ticket dependency graph and ownership matrix | Map all 100 tickets to epics, owner type, blockers, and acceptance proof. |
| CTX-010 | R | Establish weekly architecture/review gate | Reuse existing review/evidence conventions; record decisions, P0s, and demo claims. |

### Epic B — Shared runtime, app composition, and local/durable profiles (CTX-011–020)

| ID | Type | Ticket | Reuse / completion target |
| --- | --- | --- |
| CTX-011 | N | Implement CortexRuntime composition root | Construct one service graph for repositories, bus, ingestion, retrieval, evidence, and index services. |
| CTX-012 | E | Create FastAPI lifespan wiring for CortexRuntime | Extend api/app.py so routes receive dependencies instead of constructing defaults. |
| CTX-013 | E | Create local HackathonRuntime profile | Compose local Postgres/FTS, object-store-compatible adapter, journal, and optional local Qdrant without a second data model. |
| CTX-014 | E | Create durable service-profile factory | Reuse workers/factory.py and platform/factory.py to build Postgres/Kafka/object-storage/Qdrant clients. |
| CTX-015 | E | Remove connector-local default stores in profile mode | Make Slack/GitHub fail fast when services are not injected. |
| CTX-016 | E | Create shared pipeline drain interface | Reuse InMemoryPipelineDispatcher and SqlPipelineDispatcher behind one stage-handler contract. |
| CTX-017 | N | Add single-process local queue/lock semantics | Ensure webhook acknowledgement is decoupled from serialized background processing in local mode. |
| CTX-018 | E | Add runtime health and dependency readiness endpoint | Report Postgres, object storage, Kafka, FTS, Qdrant, and worker readiness. |
| CTX-019 | E | Add profile-selection safety checks | Reject invalid combinations such as memory-only state labeled durable or multiple local workers. |
| CTX-020 | N | Add app-composition end-to-end test harness | Prove one runtime serves connector ingest, retrieval API, and MCP proxy across process boundaries. |

### Epic C — Canonical ingestion, backfill, ledger, and replay (CTX-021–030)

| ID | Type | Ticket | Reuse / completion target |
| --- | --- | --- |
| CTX-021 | E | Implement transactional raw-event outbox and shared RawEventEmitter | Reuse ingestion/service.py and durable.py; atomically persist event/outbox intent before publish. |
| CTX-022 | E | Add durable ingestion-run and ingest-ledger records | Persist source/job/event/object/chunk/index counts, stage timestamps, errors, and trace IDs. |
| CTX-023 | E | Add outbox publisher/reconciliation plus cursor checkpointing | Reuse Slack cursor/backfill patterns; repair unpublished events and checkpoint each page. |
| CTX-024 | E | Make idempotency/upserts atomic across raw event, object, chunk, and index jobs | Replace check-then-insert race paths with conflict-safe database writes. |
| CTX-025 | E | Implement delayed retry scheduler and repair API | Support queued/running/retrying/failed/completed, bounded backoff, and visible last error. |
| CTX-026 | E | Add durable SQL raw-event replay CLI/API | Replace the in-memory-only replay path with provider/source/date/trace scoped repair. |
| CTX-027 | E | Implement dead-letter inspection and replay workflow | Reuse Kafka consumer error handling; attach operator-safe diagnostics. |
| CTX-028 | N | Add manifest bootstrap command | Rebuild baseline connections, payloads, objects, chunks, indexes, and ledger deterministically. |
| CTX-029 | E | Add ingest-status API and CLI | Report current cursor, latest event, stage counts, lag, and failure state. |
| CTX-030 | N | Add source-to-search recovery test | Clean startup → bootstrap → replay → query must reproduce expected source/chunk/evidence state. |

### Epic D — Slack, GitHub, and shared connector mechanics (CTX-031–040)

| ID | Type | Ticket | Reuse / completion target |
| --- | --- | --- |
| CTX-031 | E | Inject CortexRuntime into Slack service | Rewire connectors/slack/service.py to use shared ingestion/chunk/retrieval state. |
| CTX-032 | R | Complete Slack OAuth/source-selection profile path | Reuse oauth.py and sources.py with real connection persistence. |
| CTX-033 | E | Run Slack history/thread backfill through shared pipeline | Reuse backfill.py; generate truthful ledger/cursor receipts. |
| CTX-034 | E | Make Slack webhook acknowledgement asynchronous and idempotent | Reuse webhooks.py verification; enqueue then acknowledge and drain safely. |
| CTX-035 | E | Add live Slack source-to-search test | A selected real message must become cited lexical/hybrid evidence with trace IDs. |
| CTX-036 | E | Persist GitHub source connection/install state | Extend github service/setup beyond in-memory default state. |
| CTX-037 | R | Build GitHub snapshot importer through RawEventInput | Reuse github client and normalizer for repos, issues, PRs, commits, comments. |
| CTX-038 | E | Implement GitHub incremental backfill and cursors | Add bounded pagination, checkpointing, idempotency, and source receipts. |
| CTX-039 | E | Implement GitHub webhook verification and queueing | Add signed delivery verification, selected-repo filtering, and repair behavior. |
| CTX-040 | E | Add Slack/GitHub cross-source relationship linker | Reuse relationships service to connect PR, commit, issue, channel/thread, and handoff citations. |

### Epic E — Google Workspace, Atlassian, repo docs, and import framework (CTX-041–050)

| ID | Type | Ticket | Reuse / completion target |
| --- | --- | --- |
| CTX-041 | N | Build generic versioned snapshot-import framework | Validate manifest, provenance, access scope, content hashes, and RawEventInput emission. |
| CTX-042 | R | Harden repo-docs importer for shared pipeline | Reuse connectors/repo_docs and normalizer; add manifest/citation parity. |
| CTX-043 | N | Implement Google Workspace/Drive snapshot importer | Import selected Docs/Drive export with stable provider refs and revision metadata. |
| CTX-044 | N | Implement Google Workspace OAuth/source discovery | Add consent, selected drives/folders/files, and connection health. |
| CTX-045 | N | Implement Google change-cursor incremental sync | Add Drive/Docs cursor/checkpoint/retry and deletion handling. |
| CTX-046 | N | Implement Jira snapshot importer | Import projects/issues/comments/sprints with stable issue/revision references. |
| CTX-047 | N | Implement Confluence snapshot importer | Import spaces/pages/attachments/version metadata through shared normalization. |
| CTX-048 | N | Implement Atlassian OAuth/source discovery | Add selected projects/spaces and connection health. |
| CTX-049 | N | Implement Atlassian webhook/change-sync worker | Normalize Jira/Confluence increments, deletes, and retries. |
| CTX-050 | E | Create source capability/status registry | Display each source as live, indexed snapshot, extraction-ready, stale, failed, or disabled. |

### Epic F — Object storage, files, images, audio, and video (CTX-051–060)

| ID | Type | Ticket | Reuse / completion target |
| --- | --- | --- |
| CTX-051 | E | Implement S3-compatible ObjectStorage adapter | Fulfill interfaces/storage.py using S3/R2/GCS-compatible semantics; support local MinIO profile. |
| CTX-052 | E | Implement object-backed PayloadStore adapter | Unify raw payload offload with ObjectStorage while retaining hashes and replay semantics. |
| CTX-053 | E | Extend SourceFile/media schema and migration | Add size, provider ref, extraction status/version, page/time/frame provenance, manifest object key, and safe citation fields. |
| CTX-054 | N | Implement provider-ID file fetch worker | Fetch with connector credentials, not retained private URLs; honor selected source and ACL policy. |
| CTX-055 | N | Implement media validation and quarantine policy | Enforce MIME sniffing, size limits, checksum, malware/scanning hook, retry, and retention rules. |
| CTX-056 | N | Implement image/PDF OCR extraction worker | Persist versioned OCR artifacts and page/image chunks with provenance. |
| CTX-057 | N | Implement audio transcription worker | Produce timestamped transcript segments and language/model provenance. |
| CTX-058 | N | Implement video extraction worker | Produce sampled/keyframe captions/OCR plus timecoded transcript/keyframe manifest. |
| CTX-059 | E | Add extraction-job scheduler and lifecycle | Model discovered/fetching/fetched/extracting/extracted/failed/stale/deleted with replay. |
| CTX-060 | E | Add media evidence/citation renderer | Return authorized page/time/frame references and source links without exposing private URLs. |

### Epic G — Indexing, hybrid retrieval, and evaluation (CTX-061–070)

| ID | Type | Ticket | Reuse / completion target |
| --- | --- | --- |
| CTX-061 | E | Implement true PostgreSQL FTS index jobs and retrieval | Replace Python substring matching with tsvector/tsquery scoring over canonical SourceChunk text. |
| CTX-062 | N | Implement production Qdrant VectorIndex adapter | Fulfill interfaces/vector_index.py for collection creation, upsert, filtered search, health, and delete. |
| CTX-063 | E | Wire real embedding completion to vector-index jobs | Reuse embeddings service/publishers and index repositories; preserve model/version/hash provenance. |
| CTX-064 | E | Implement IndexReadiness projection worker | Join lexical/vector job outcomes into lexical_ready, vector_ready, hybrid_ready, partial, failed. |
| CTX-065 | E | Add real embedding-provider configuration and secret handling | Reuse Gemini provider/config boundaries; allow model/dimension/version rotation. |
| CTX-066 | E | Implement hybrid candidate fusion | Reuse candidate/ranking models; add reciprocal-rank fusion, dedupe, source diversity, and configurable weights. |
| CTX-067 | E | Push authorization filters into FTS and Qdrant queries | Reuse permission service; filter before hydration and after relationship expansion. |
| CTX-068 | E | Add freshness/partial-result policy | Make lagging/failed index paths visible in evidence packs and agent output. |
| CTX-069 | E | Add durable context-gate/canonical-memory repositories and ranking hooks | Reuse existing policies/models; add SQL transactions, audit, active-decision boost, and relationship expansion. |
| CTX-070 | E | Build hybrid retrieval evaluation harness | Golden lexical, paraphrase, cross-source, no-result, ACL, freshness, canonical, and media queries with regressions. |

### Epic H — MCP, agent handoffs, and agent-native delivery (CTX-071–080)

| ID | Type | Ticket | Reuse / completion target |
| --- | --- | --- |
| CTX-071 | N | Add pinned MCP SDK and cortex-mcp CLI entrypoint | Keep stdout protocol-only, logs on stderr, and package/run documentation. |
| CTX-072 | N | Implement stateless stdio MCP proxy transport | Proxy to authenticated local/hosted Cortex API; define connect/read timeout and unavailable response. |
| CTX-073 | E | Implement proxy credential and workspace/actor derivation | Tools omit caller-supplied identity; server binds token to workspace/actor/repo context. |
| CTX-074 | E | Implement retrieval/evidence API boundary | Move tool business logic out of global mcp/server.py and onto shared Cortex services. |
| CTX-075 | N | Implement P0 MCP tools | Ship retrieve_context, get_handoff, and source_status with schemas and protocol tests. |
| CTX-076 | E | Implement evidence resource/deep-link contract | Add bounded authorized evidence fetch plus citation/trace metadata. |
| CTX-077 | N | Define handoff-v1 artifact and importer | Version, owner, recipients, repo/branch/commit, segments, citations, expiry/revocation, content hash. |
| CTX-078 | N | Implement session redaction/validation pipeline | Best-effort secret/path filtering, schema validation, consent capture, and rejection reporting. |
| CTX-079 | N | Implement handoff sharing/revocation policy | Support owner/recipient permissions, expiry, revoke/tombstone, and audit tests. |
| CTX-080 | E | Implement Claude Code continuation preflight | Generate a cited continuation pack; only surface native resume/fork after transcript/cwd compatibility is verified. |

### Epic I — Security, lifecycle, observability, reliability, and operations (CTX-081–090)

| ID | Type | Ticket | Reuse / completion target |
| --- | --- | --- |
| CTX-081 | E | Apply tenant context to every new API/worker path | Reuse tenancy/auth dependencies; prevent workspace selection through tool arguments. |
| CTX-082 | E | Propagate provider ACL snapshots through normalization and retrieval | Reuse permissions/provider_acl modules; add source/file/chunk filters and revocation tests. |
| CTX-083 | E | Add audit events for source, evidence, and handoff operations | Reuse security/audit patterns; make actor/source/evidence access observable. |
| CTX-084 | E | Complete retention and lifecycle deletion across all stores | Reconcile retention-policy defaults; include objects, extraction artifacts, FTS, Qdrant, evidence cache, exports, and tombstones. |
| CTX-085 | E | Add pipeline metrics and source freshness dashboards/API | Reuse observability metrics/tracing; expose ingestion, extraction, index, retry, and lag measures. |
| CTX-086 | E | Add end-to-end trace propagation | Reuse tracing; correlate connector delivery, Kafka event, job, evidence pack, and MCP request. |
| CTX-087 | E | Add backpressure/rate-limit/DLQ policy per source and model | Reuse platform rate limits and Kafka failure handling; publish operator states. |
| CTX-088 | E | Implement backup/restore and derived-index rebuild for media | Extend backup/restore and derived-index smoke scripts to object storage + Qdrant. |
| CTX-089 | E | Add deployment/secret-boundary hardening | Reuse deployment config/tests; require secrets manager boundaries, loopback MCP, health checks, and safe logs. |
| CTX-090 | N | Write threat model and incident runbook for agent context | Cover provider tokens, transcript leaks, media abuse, tenant escape, index lag, and unsafe continuation. |

### Epic J — Evidence console, demo, documentation, and packaging (CTX-091–100)

| ID | Type | Ticket | Reuse / completion target |
| --- | --- | --- |
| CTX-091 | E | Implement read-only evidence/ingestion status API | Expose real source, event, object, chunk, extraction, index, and query-evidence counts. |
| CTX-092 | E | Implement CLI evidence console | Reuse Typer/observability; provide a UI-independent proof surface for demo and debugging. |
| CTX-093 | E | Define dashboard data contracts and UI states | Empty, connecting, backfilling, indexing, ready, partial, failed/retryable, revoked. |
| CTX-094 | E | Wire one minimal source-health/control-plane view | Preserve existing frontend work; connect only to stable status/evidence APIs. |
| CTX-095 | N | Build focused Cortex Handoff view | Show source timeline, cited evidence, approval state, continuation pack, and copy/open action. |
| CTX-096 | N | Create sanitized multi-source demo corpus | Slack, GitHub, approved handoff, docs/imports, and actual extracted media with manifests. |
| CTX-097 | E | Create deterministic demo bootstrap and rehearsal runner | Seed/replay, execute golden queries, verify counts/citations, and retain trace artifacts. |
| CTX-098 | N | Write production-quality README | Product claim, architecture, quickstart, MCP setup, sources, privacy, limitations, and demo path. |
| CTX-099 | N | Produce pitch/slides and evidence-backed script | Build from real traces, source coverage, and approved claims only. |
| CTX-100 | N | Record demo video and run release gate | Validate every on-screen claim against ledger/evidence; package screenshots and final runbook. |

### Epic K — Cleanup, deprecation, and removal safety (CTX-101–110)

No ticket in this epic authorizes blind deletion. Each one starts with an inventory, owner, dependency check, replacement/migration proof, and a focused test. The current uncommitted frontend worktree is explicitly excluded.

| ID | Type | Ticket | Reuse / completion target |
| --- | --- | --- |
| CTX-101 | N | Create a deprecated/unused-component inventory | Catalog every fixture-only runtime path, unused route, env var, worker event, script, and duplicate store with owner and removal criterion. |
| CTX-102 | E | Remove fixture retrieval defaults from non-test execution paths | Keep deterministic fixtures under tests/dev only; production/local profiles must fail if they select seeded global retrieval. |
| CTX-103 | E | Retire connector-local default stores after runtime injection | Follow CTX-015; delete or quarantine Slack/GitHub local repositories only after app-composition tests prove replacement. |
| CTX-104 | E | Make unsupported pipeline events fail visibly | Replace silent no-op/commit behavior with explicit handling, DLQ, or a deliberate retirement record. |
| CTX-105 | E | Consolidate PayloadStore and ObjectStorage boundaries | After CTX-051/052, remove duplicated production byte-storage paths while retaining test adapters behind explicit test-only factories. |
| CTX-106 | E | Retire filesystem payload-volume production wiring | Only after object-store migration, backup/restore, and replay tests pass; preserve local dev adapter separately. |
| CTX-107 | E | Retire in-memory vector runtime path from non-test profiles | Keep it for deterministic tests only after real Qdrant adapter/readiness tests are green. |
| CTX-108 | E | Reconcile legacy FastAPI UI and Next.js frontend boundaries | Define ownership/migration; do not alter the dirty frontend worktree until its owner creates a safe commit/review boundary. |
| CTX-109 | E | Refresh stale README, phase docs, smoke scripts, and configuration | Align claims with executable paths; repair or retire broken Kafka Slack smoke and unused placeholder settings. |
| CTX-110 | N | Add a cleanup release gate | Block release when deprecated paths remain enabled, docs overclaim, dead config is loaded, or removal evidence is missing. |

## Recommended execution lanes

| Lane | First tickets | Why it is a dependency |
| --- | --- | --- |
| One real data path | CTX-011–020, CTX-021–030, CTX-031–035 | Removes the split-state problem and proves a Slack message can reach retrieval. |
| Durable media/storage | CTX-051–055, CTX-061–065 | Gives the product proper source-of-truth and enables images/video without fake claims. |
| Hybrid context retrieval | CTX-061–070 | Makes the actual differentiator: keyword precision plus semantic recall with citations. |
| Agent delivery | CTX-071–080 | Makes Cortex an MCP layer rather than another chat app. |
| Source breadth | CTX-036–050 | Adds GitHub, Workspace, and Atlassian on a shared adapter contract. |
| Trust and operations | CTX-081–090 | Makes tenant, deletion, evidence, and recovery stories real. |
| Demo/product packaging | CTX-091–100 | Converts technical proof into a judge-ready experience after the data path is credible. |
| Cleanup/deprecation | CTX-101–110 | Prevents the new path from coexisting indefinitely with fixtures, duplicate stores, stale claims, and unsafe removals. |

## First 20 tickets to start

Start in this order: CTX-001, CTX-002, CTX-004, CTX-011, CTX-012, CTX-015, CTX-016, CTX-021, CTX-022, CTX-031, CTX-033, CTX-034, CTX-051, CTX-052, CTX-061, CTX-062, CTX-063, CTX-064, CTX-071, CTX-074.

That sequence preserves the full architecture while making a genuinely queryable Slack → hybrid evidence → MCP path the first vertically complete slice.

## Validation baseline already available

The project already contains broad unit/smoke coverage that can be extended rather than replaced:

- Ingestion/payload/replay: tests/ingestion/ and tests/contracts/; add a real Postgres/Kafka outbox and concurrent-delivery suite before treating it as durable.
- Slack connector/backfill/webhook/health: tests/connectors/slack/.
- Retrieval/evidence/permissions: tests/retrieval/; current coverage is largely in-memory and must gain Postgres FTS/Qdrant integration cases.
- Workers/Kafka/embeddings: tests/workers/ and tests/events/.
- Indexing/lifecycle: tests/indexing/ and tests/lifecycle/.
- Tenancy/security/provider ACL: tests/tenancy/, tests/security/, tests/permissions/.
- API/deployment/ops: tests/api/, tests/deployment/, tests/backup/, scripts/.

The key new test category is **application composition**: a real connector event must travel through the same runtime seen by the authenticated MCP process and return a cited evidence pack.
