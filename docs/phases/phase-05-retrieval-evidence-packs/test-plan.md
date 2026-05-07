# Phase 5 Test Plan

## Commands

```bash
ruff check .
ruff format --check .
mypy src
pytest
```

Focused local loop:

```bash
pytest tests/retrieval tests/mcp tests/indexing tests/dev
```

Optional database smoke when local Postgres is available:

```bash
docker compose up -d postgres
alembic upgrade head
pytest tests/retrieval/test_postgres_fts_retriever.py
```

## Coverage Map

```txt
Config
  -> candidate/ranking/token budget YAML defaults match ADR
  -> typed loader rejects invalid limits/weights
  -> base ranking weights must sum to 1.0

Persistence
  -> retrieval_requests lifecycle
  -> evidence_packs lifecycle
  -> config versions recorded
  -> sensitive query/snippet content not logged

Query planner
  -> COR-123 issue extraction
  -> PR number/file path/source filters
  -> source allowlist snapshot hash

Candidate retrieval
  -> Postgres FTS candidates
  -> VectorIndex candidates
  -> relationship expansion candidates
  -> workspace/status/version filters
  -> candidate limits from config
  -> single candidate path failure returns partial_results
  -> all candidate paths failing marks request failed

Permissions
  -> non-allowlisted chunks excluded before ranking
  -> exclusion summaries do not leak names/URLs/snippets/debug IDs
  -> permission ambiguity yields partial/failed safe state

Ranking
  -> deterministic score merge
  -> exact issue/PR evidence ranks
  -> max chunks per source object enforced
  -> stale evidence remains visible but flagged/lower-ranked

Evidence packs
  -> claims/citations/source coverage
  -> every citation resolves
  -> token budget and snippet limits
  -> missing/stale/conflict summaries
  -> compact text plus structured JSON

MCP tools
  -> retrieve_context success/error
  -> get_related_work success/error
  -> no gate status returned

Events/evals
  -> evidence_pack.created envelope
  -> golden COR-123 retrieval
  -> Recall@K/MRR/citation accuracy/permission safety/latency/token count
```

## Tests To Create

| Test file | Assertions |
| --- | --- |
| `tests/retrieval/test_retrieval_config.py` | Candidate/ranking/token budget config matches ADR, validates bounds, and rejects ranking weights that do not sum to 1.0. |
| `tests/retrieval/test_retrieval_repositories.py` | Retrieval request/evidence pack lifecycle, versions, expiry, no content logs. |
| `tests/retrieval/test_query_planner.py` | COR-123, PR numbers, paths, filters, allowlist snapshot hash. |
| `tests/retrieval/test_postgres_fts_retriever.py` | Workspace-scoped FTS candidates and limits. |
| `tests/retrieval/test_vector_retriever.py` | VectorIndex search filters, query embedding, limits. |
| `tests/retrieval/test_relationship_expansion.py` | Related issue/PR/thread/doc expansion with allowlists. |
| `tests/retrieval/test_candidate_failures.py` | FTS/vector/relationship single-path failures produce partial results; all-path failures mark request failed. |
| `tests/retrieval/test_permission_filter.py` | Non-allowlisted exclusion and safe summaries. |
| `tests/retrieval/test_ranking.py` | Deterministic merge/scoring, exact ID ranking, per-source cap. |
| `tests/retrieval/test_evidence_pack_builder.py` | Claims, citations, coverage, stale/missing/conflict summaries, token budget. |
| `tests/retrieval/test_evidence_pack_publisher.py` | Exact `evidence_pack.created` envelope and forbidden payload protection. |
| `tests/mcp/test_retrieve_context.py` | MCP success/error shape and no gate status. |
| `tests/mcp/test_get_related_work.py` | Related-work output shape and citations. |
| `tests/retrieval/test_golden_cor_123.py` | Golden query evidence and metrics. |

## Golden COR-123 Assertions

Minimum expected evidence:

- Slack Postgres-session decision,
- Slack diagram OCR,
- GitHub PR `184`,
- Linear `COR-119` blocker,
- stale Redis session docs.

Minimum evidence pack fields:

```json
{
  "claims_json": {},
  "citations_json": {},
  "source_coverage_json": {},
  "permission_exclusions_json": {},
  "stale_context_json": {},
  "conflict_summary_json": {},
  "token_budget": 4000,
  "ranker_version": "ranking-v1"
}
```

Minimum MCP response:

```json
{
  "ok": true,
  "retrieval_request_id": "ret_...",
  "evidence_pack_id": "ep_...",
  "text": "compact cited context",
  "evidence_pack": {}
}
```

The response must not include `allow`, `warn`, or `block`; Phase 6 owns gate
status.

## Not Required In Phase 5

- `check_context_gate` behavior tests,
- canonical approval tests,
- LLM reranking/synthesis tests,
- real provider ACL snapshot tests,
- real provider embedding tests,
- browser tests.
