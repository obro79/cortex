from __future__ import annotations

from pathlib import Path


def test_cache_docs_define_redis_as_ephemeral_only() -> None:
    docs = Path("docs/platform/cache.md").read_text()

    assert "must never become an authority" in docs
    assert "Redis is not required for local development" in docs
    assert "connector cursors" in docs
    assert "permissions, or audit" in docs
    assert "Qdrant and OpenSearch are derived indexes" in docs
