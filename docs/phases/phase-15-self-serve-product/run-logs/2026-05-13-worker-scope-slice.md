# 2026-05-13 Worker Scope Slice

## Completed

- Added resource ownership checks before worker handlers act on loaded records:
  - raw event normalization verifies envelope and raw event workspace match,
  - source object/file chunking verifies envelope and source record workspace
    match,
  - embedding queue/complete verifies envelope, chunk, and embedding record
    workspace match.
- Kept mismatch behavior non-revealing by ignoring the work item with a
  `workspace_mismatch` reason instead of processing cross-workspace records.
- Added focused regression tests for normalization worker, normalization
  service, chunking service, and embedding worker cross-workspace events.

## Validation

```bash
uv run pytest tests/workers/test_normalization_worker.py tests/normalization/test_normalization_service.py tests/workers/test_embedding_worker.py tests/chunking/test_workspace_ownership.py
uv run ruff check src/cortex/normalization/service.py src/cortex/chunking/service.py src/cortex/embeddings/service.py src/cortex/workers/embeddings.py src/cortex/workers/normalization.py tests/workers/test_normalization_worker.py tests/normalization/test_normalization_service.py tests/workers/test_embedding_worker.py tests/chunking/test_workspace_ownership.py
```

Result: both passed.
