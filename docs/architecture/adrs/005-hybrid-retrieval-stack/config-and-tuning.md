# Retrieval Configuration And Tuning

## Purpose

Retrieval has tunable parameters. Treat them as versioned configuration, not
magic constants. The first implementation should pick conservative defaults,
store the versions that produced each result, and tune only when evals show a
retrieval failure.

Do not tune by vibes. Tune against golden eval cases.

## Config Buckets

### Chunking

Chunking controls how source objects become retrievable units.

V1 defaults:

```txt
global_min_chunk_tokens = 120
global_max_chunk_tokens = 1200

docs_target_tokens = 800
docs_overlap_tokens = 100

slack_thread_target_tokens = 600
slack_message_overlap_count = 1

linear_issue_target_tokens = 700
linear_comment_overlap_count = 1

github_pr_target_tokens = 900
ocr_target_tokens = 600
ocr_overlap_tokens = 100
```

Source-specific rules matter more than one universal chunk size:

| Source | Strategy | Target | Overlap |
| --- | --- | ---: | --- |
| Slack thread | overview chunk + message-window chunks | 400-800 tokens | 1 message |
| Linear issue | issue overview + comment groups | 400-800 tokens | 1 comment summary |
| GitHub PR | PR overview + review/comment chunks | 500-1000 tokens | section boundary only |
| Repo docs | markdown heading sections | 500-1200 tokens | 100 tokens |
| Diagram/OCR | metadata chunk + OCR text chunk | 300-800 tokens | 0-100 tokens |
| Canonical decision | compact decision chunk | 150-500 tokens | none |

Tuning signals:

- expected evidence missed because the chunk was too broad,
- expected evidence missed because related context split across boundaries,
- too many duplicate chunks in final evidence,
- evidence snippets too long for agent output.

### Embeddings

Embedding config controls vector representation.

V1 defaults:

```txt
dev_embedding_provider = deterministic
prod_embedding_provider = gemini
prod_embedding_model = gemini-embedding-2
prod_embedding_dimensions = 1536
embedding_batch_size = 32
embedding_version = gemini2-1536-v1
```

Rules:

- dev/test uses deterministic embeddings for stable tests,
- production uses provider adapters through the model gateway,
- every embedding record stores provider, model, dimensions, task type, content
  hash, chunking version, embedding version, and status,
- changing model or dimensions requires a new `embedding_version` and index
  rebuild.

Tuning signals:

- semantic queries miss paraphrased decisions,
- exact identifiers work but conceptual recall is weak,
- latency/cost is too high for embedding batches.

### Candidate Retrieval

Candidate retrieval controls how much evidence is pulled before ranking.

V1 defaults:

```txt
fts_candidate_limit = 50
vector_candidate_limit = 50
relationship_expansion_limit = 20
merged_candidate_limit = 75
final_evidence_limit = 12
max_chunks_per_source_object = 3
```

Tradeoff:

- higher limits improve recall but increase latency and ranking noise,
- lower limits improve speed but can miss constraints.

Tuning signals:

- expected evidence exists in indexes but is not in candidate sets,
- final evidence contains too many near-duplicates,
- retrieval latency exceeds target.

### Ranking

Ranking merges lexical, vector, relationship, recency, and authority signals.

V1 starting weights:

```txt
vector_weight = 0.45
lexical_weight = 0.30
recency_weight = 0.10
relationship_weight = 0.10
source_authority_weight = 0.05
canonical_decision_boost = 0.20
```

These weights are a starting point, not truth. Keep the ranking function simple
until evals show a specific failure.

Tuning signals:

- stale evidence ranks above newer canonical decisions,
- exact issue IDs rank below semantically similar but unrelated chunks,
- weak relationship candidates dominate direct evidence.

### Context Gate

Gate config controls `allow`, `warn`, and `block`.

V1 defaults:

```txt
high_confidence_conflict_threshold = 0.80
stale_context_days = 90
min_required_sources_for_high_risk_tasks = 2
block_on_permission_uncertainty = true
block_on_high_confidence_architecture_conflict = true
warn_on_missing_low_risk_context = true
```

Rules:

- block only high-confidence, high-impact conflicts in v1,
- warn for lower-risk ambiguity,
- fail closed on permission ambiguity,
- every warn/block must cite evidence.

Tuning signals:

- gate blocks too often on weak or uncited conflicts,
- gate allows implementation when fixture evidence is intentionally
  contradictory,
- users repeatedly choose "proceed with warning" for the same category.

### Token Budget

Token budget controls agent-facing output.

V1 defaults:

```txt
max_evidence_pack_tokens = 4000
max_claims = 8
max_citations_per_claim = 3
max_snippet_tokens = 180
max_missing_context_items = 5
max_conflict_items = 5
```

Tuning signals:

- agent output is too noisy,
- citations lack enough context to be actionable,
- important conflict details get truncated.

## Versioning

Store versions on records and outputs:

```txt
chunking_version = slack-thread-v1
embedding_version = gemini2-1536-v1
retrieval_config_version = retrieval-v1
ranker_version = ranker-v1
gate_version = gate-v1
index_version = qdrant-v1
```

Version changes:

- chunking change -> mark affected chunks stale and rebuild chunks/embeddings/indexes,
- embedding model/dimension change -> create new embedding records and rebuild vector index,
- ranking/config change -> no reindex required, but evidence packs should record the version,
- gate change -> no reindex required, but gate results should record the version.

## Qdrant Interface

Use an adapter interface. Application code should not call Qdrant directly.

```python
class VectorIndex:
    async def ensure_collection(self, name: str, dimensions: int) -> None: ...
    async def upsert_points(self, collection: str, points: list[VectorPoint]) -> None: ...
    async def delete_points(self, collection: str, point_ids: list[str]) -> None: ...
    async def search(self, collection: str, vector: list[float], filters: VectorFilters, limit: int) -> list[VectorHit]: ...
    async def health(self) -> VectorIndexHealth: ...
```

Qdrant payload should contain filterable metadata, not source text:

```json
{
  "workspace_id": "ws_1",
  "source_object_id": "so_456",
  "source_chunk_id": "chunk_789",
  "provider": "slack",
  "source_type": "slack_thread",
  "chunk_type": "thread_window",
  "chunking_version": "slack-thread-v1",
  "embedding_model": "gemini-embedding-2",
  "embedding_version": "gemini2-1536-v1",
  "status": "active"
}
```

Required filters:

```txt
workspace_id
source allowlist eligibility
chunk status = active
chunking_version = current
embedding_version = current
provider/source filters from query
```

Never search across tenants. Never return chunks outside the source allowlist.

## Eval-Driven Tuning

Every config change should be compared against golden evals.

Required v1 metrics:

```txt
Recall@K
MRR
citation_accuracy
conflict_detection_accuracy
gate_accuracy
latency_ms
evidence_pack_tokens
```

Example eval case:

```json
{
  "query": "I'm implementing COR-123 session migration. What context constrains this?",
  "expected_evidence": [
    "Slack Postgres decision thread",
    "Slack architecture diagram OCR",
    "GitHub session migration PR",
    "Linear blocker issue",
    "stale Redis docs"
  ],
  "expected_gate": "block"
}
```

Promotion rule:

- keep the simpler config unless the new config improves at least one target
  metric without regressing citation accuracy, gate accuracy, or permission
  safety,
- any config that reduces permission safety is rejected regardless of recall.
