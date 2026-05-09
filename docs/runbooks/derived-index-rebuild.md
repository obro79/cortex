# Derived Index Rebuild Runbook

Qdrant and OpenSearch are derived indexes. They must be rebuildable from
Postgres source objects, chunks, embeddings, raw-event pointers, and object
storage payloads.

## Rebuild Order

1. Confirm Postgres and object storage are healthy.
2. Pause new indexing workers or route rebuild work to an isolated collection.
3. Recompute source chunks from normalized source objects and source files.
4. Recompute embeddings for chunks missing the target embedding version.
5. Reinsert vectors and searchable metadata into the derived index.
6. Run retrieval eval parity against the fixture workspace.
7. Swap traffic to the rebuilt collection only after parity passes.

## Parity Requirement

The rebuild passes when known retrieval queries return the expected evidence
IDs, source types, and context-gate decisions. The check must compare IDs and
statuses, not private snippets or raw source content.

## Smoke Command

```bash
python scripts/derived_index_rebuild_smoke.py --static
python scripts/derived_index_rebuild_smoke.py --list
```

Use `--full` only with disposable local or staging index targets.
