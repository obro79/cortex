# Phase 5 Plan: Retrieval And Evidence Packs

## Goal

Return task-specific, permission-safe, cited context instead of broad memory
dumps.

Phase 5 starts where Phase 4 stops:

```txt
retrieve_context / get_related_work
  -> retrieval_request
  -> query planner and source allowlist snapshot
  -> Postgres FTS candidates
  -> VectorIndex candidates
  -> deterministic relationship expansion
  -> permission/source allowlist filter
  -> rank and merge
  -> evidence_pack
  -> compact agent text + structured JSON
  -> evidence_pack.created
```

This phase does not decide `allow`, `warn`, or `block`; Phase 6 owns context
gate decisions. Phase 5 can surface stale, conflicting, missing, and excluded
context as evidence-pack fields for the gate to consume.

## Inputs

- [`../implementation-roadmap.md`](../implementation-roadmap.md#phase-5-retrieval-and-evidence-packs)
- [`../../architecture/v1-entity-state-schema.md`](../../architecture/v1-entity-state-schema.md#retrieval_requests)
- [`../../architecture/pipeline-event-envelope.md`](../../architecture/pipeline-event-envelope.md)
- [`../../architecture/adrs/005-hybrid-retrieval-stack/README.md`](../../architecture/adrs/005-hybrid-retrieval-stack/README.md)
- [`../../architecture/adrs/005-hybrid-retrieval-stack/config-and-tuning.md`](../../architecture/adrs/005-hybrid-retrieval-stack/config-and-tuning.md)
- [`../../architecture/adrs/009-source-allowlist-permissions-v1/README.md`](../../architecture/adrs/009-source-allowlist-permissions-v1/README.md)
- [`../../architecture/adrs/016-retrieval-evals-model-gateway/README.md`](../../architecture/adrs/016-retrieval-evals-model-gateway/README.md)
- [`../phase-04-chunking-indexing/plan.md`](../phase-04-chunking-indexing/plan.md)
- [`../../../config/retrieval-v1.yaml`](../../../config/retrieval-v1.yaml)

## Existing Foundation

Earlier phases provide:

- normalized source objects/files,
- source chunks with citations,
- Postgres FTS and vector adapter/index metadata,
- deterministic embeddings,
- relationship seeds,
- `RetrievalRequest` and `EvidencePack` contracts,
- MCP tool names for `retrieve_context` and `get_related_work`,
- versioned retrieval config.

## Non-Goals

- No context gate status computation.
- No canonical decision approvals.
- No LLM answer synthesis or reranking.
- No real provider ACL snapshots beyond source allowlist filtering.
- No new indexing or embedding behavior.
- No browser/UI evidence-pack viewer beyond existing dev-workbench hooks.

## Architecture

```txt
RetrievalService
  -> create RetrievalRequest(status=received)
  -> QueryPlanner
      -> normalized query
      -> task hints
      -> provider/source filters
      -> source allowlist snapshot hash
  -> CandidateRetrieval
      -> PostgresFtsRetriever
      -> VectorRetriever
      -> RelationshipExpander
  -> PermissionFilter
  -> CandidateMerger
  -> Ranker
  -> EvidencePackBuilder
  -> AgentTextRenderer
  -> EvidencePackRepository.create()
  -> EvidencePackPublisher.evidence_pack.created
  -> mark RetrievalRequest completed / partial_results / failed
```

All candidate stages must preserve enough debug metadata for the evidence pack
`candidate_summary_json`, but the final output must not expose non-allowlisted
source names, URLs, file names, snippets, or debug IDs.

## Proposed Module Layout

```txt
src/cortex/retrieval/
  __init__.py
  config.py
  query.py
  candidates.py
  fts.py
  vector.py
  relationships.py
  permissions.py
  ranking.py
  evidence.py
  render.py
  service.py
  publishers.py

tests/retrieval/
tests/mcp/
```

Keep the initial implementation deterministic. Add model-based reranking only
after evals prove the need.

## Data Model

Add SQLAlchemy records and migrations for:

- `retrieval_requests`,
- `evidence_packs`.

Fields, indexes, and lifecycle states should match
`v1-entity-state-schema.md`.

Query text and evidence snippets can contain sensitive content. Logs should use
retrieval request IDs, evidence pack IDs, trace IDs, hashes, counts, statuses,
and latencies rather than full query text or snippets.

Evidence packs should record:

- `retrieval_config_version`,
- candidate retrieval version,
- ranker version,
- token budget version,
- source allowlist snapshot hash.

If the current `EvidencePack` contract only has `ranker_version`, extend it or
store the additional versions in structured JSON fields.

## Retrieval Config

Use [`config/retrieval-v1.yaml`](../../../config/retrieval-v1.yaml) through a
typed loader.

Phase 5 uses:

- `candidate_retrieval`,
- `ranking`,
- `token_budget`,
- embedding/chunking version filters produced by Phase 4.

The typed loader should reject missing sections, unknown strategy/version names,
invalid numeric bounds, ranking weights that do not have an explicit version,
negative weights, and base ranking weights that do not sum to `1.0`. Boosts
such as `canonical_decision_boost` are additive and should be validated
separately.

## Query Planner

The query planner should parse request arguments into:

- normalized query text,
- task hints,
- issue IDs,
- PR numbers,
- file paths,
- repo/docs hints,
- provider/source filters,
- source allowlist snapshot.

Do not log raw query text. Store it only in `retrieval_requests` according to
retention policy.

## Candidate Retrieval

Postgres FTS path:

- search active chunks scoped by workspace,
- filter by current chunking version,
- filter by source allowlist,
- return FTS score and citation metadata,
- respect `fts_candidate_limit`.

Vector path:

- embed the query using the deterministic provider in dev/test,
- search `VectorIndex`,
- filter by workspace, active status, current chunking/embedding versions,
- filter by source allowlist,
- respect `vector_candidate_limit`.

Relationship expansion:

- expand from exact issue IDs, PR numbers, URLs, file paths, and deterministic
  relationship seeds,
- respect `relationship_expansion_limit`,
- do not expose non-allowlisted related source names or debug IDs.

Partial result behavior:

- if one candidate path fails, return `partial_results` with safe error metadata
  in `candidate_summary_json`,
- if all candidate paths fail, mark the retrieval request `failed`,
- if a candidate path times out, preserve candidates from successful paths and
  record the timeout without logging query text or snippets.

## Permission Filtering

Use source allowlists as the v1 permissions model.

Rules:

- never search across tenants,
- never return chunks outside the source allowlist,
- never include non-allowlisted source names, URLs, file names, snippets, chunk
  IDs, or debug IDs in evidence packs,
- record excluded counts and safe source categories in
  `permission_exclusions_json`,
- if permission ambiguity prevents safe retrieval, return partial/failed
  evidence state for Phase 6 to fail closed.

## Ranking And Merging

Merge FTS, vector, and relationship candidates into a deduplicated candidate
set. Use ranking weights from `retrieval-v1.yaml`:

- vector,
- lexical,
- recency,
- relationship,
- source authority,
- canonical decision boost placeholder.

Rules:

- cap candidates per source object with `max_chunks_per_source_object`,
- preserve all scoring components in `candidate_summary_json`,
- keep ranking deterministic for tests,
- validate that configured base ranking weights sum to `1.0`,
- do not perform LLM reranking in Phase 5.

## Evidence Pack Builder

Build evidence packs with:

- claims,
- citations,
- candidate summary,
- source coverage,
- permission exclusions,
- missing context,
- stale context,
- conflict summary,
- token budget,
- ranker/config versions.

Every citation must resolve to an allowlisted source chunk and source object/file.
Evidence packs should include compact snippets, not whole source chunks. Snippets
must obey `token_budget.max_snippet_tokens`.

The agent-facing text renderer should produce compact text plus structured JSON.
If the token budget is exceeded, drop lower-ranked evidence first and record the
omission in `missing_context_json` or candidate summary.

## MCP Tools

Implement:

- `retrieve_context`: return cited context for a task/query with structured JSON
  and compact text.
- `get_related_work`: use the same retrieval stack but bias query planning and
  ranking toward related issues, PRs, threads, docs, diagrams, and files.

Tool responses should include:

- `ok`,
- `retrieval_request_id`,
- `evidence_pack_id`,
- compact text,
- structured evidence pack fields,
- latency/status,
- safe permission exclusion summary.

Do not return a context gate status in Phase 5.

## Evaluation

Add the golden COR-123 retrieval eval:

```txt
query: "I'm implementing COR-123 session migration. What context constrains this?"
expected evidence:
  - Slack Postgres decision thread
  - Slack architecture diagram OCR
  - GitHub session migration PR
  - Linear blocker issue
  - stale Redis docs
```

Track:

- Recall@K,
- MRR,
- citation accuracy,
- permission safety,
- latency,
- evidence pack token count.

Conflict detection and gate accuracy can be placeholders until Phase 6, but the
evidence pack should expose stale/conflicting signals when fixtures make them
deterministic.

## Event Publication

Publish `evidence_pack.created` after durable evidence pack creation.

Envelope rules:

- `subject.type=evidence_pack`,
- `subject.id` is the evidence pack ID,
- `causation.retrieval_request_id` is set,
- config/ranker versions are represented,
- `payload` contains small metadata only: status, candidate counts, token budget,
  and operation.

Never include source snippets, query text, source names, URLs, file names,
non-allowlisted debug IDs, or secrets in event payloads.

## Acceptance Criteria

Phase 5 is complete when:

- `retrieval_requests` and `evidence_packs` have records and migrations.
- `retrieve_context` and `get_related_work` MCP tools return structured JSON and
  compact text.
- Hybrid FTS/vector retrieval returns allowlisted candidates only.
- Ranking is deterministic and uses versioned config.
- Evidence citations always resolve to allowlisted source chunks and source
  objects/files.
- Golden COR-123 retrieval returns Slack decision, diagram OCR, GitHub PR,
  Linear blocker, and stale Redis doc evidence.
- Max-token budget tests pass.
- `evidence_pack.created` is pointer-only and content-free.
