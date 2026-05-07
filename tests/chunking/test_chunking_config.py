from pathlib import Path

import pytest
from pydantic import ValidationError

from cortex.chunking.config import load_retrieval_config


def test_retrieval_config_loads_expected_versions() -> None:
    config = load_retrieval_config()

    assert config.version == "retrieval-config-v1"
    assert config.chunking.version == "chunking-v1"
    assert config.chunking.global_min_chunk_tokens == 120
    assert config.chunking.docs.target_tokens == 800
    assert config.embeddings.dev_provider == "deterministic"
    assert config.embeddings.prod_dimensions == 1536


def test_retrieval_config_rejects_invalid_numeric_bounds(tmp_path: Path) -> None:
    config_path = tmp_path / "bad.yaml"
    config_path.write_text(
        """
version: retrieval-config-v1
chunking:
  version: chunking-v1
  global_min_chunk_tokens: 0
  global_max_chunk_tokens: 1200
  docs:
    strategy: docs
    target_tokens: 1
  slack_thread:
    strategy: slack
    target_tokens: 1
  linear_issue:
    strategy: linear
    target_tokens: 1
  github_pr:
    strategy: github
    target_tokens: 1
  ocr:
    strategy: ocr
    target_tokens: 1
embeddings:
  version: emb-v1
  dev_provider: deterministic
  prod_provider: gemini
  prod_model: gemini
  prod_dimensions: 1536
  batch_size: 32
candidate_retrieval:
  version: c
ranking:
  version: r
""".strip()
    )

    with pytest.raises(ValidationError):
        load_retrieval_config(config_path)
