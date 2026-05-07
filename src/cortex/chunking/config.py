from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field


class SourceChunkingConfig(BaseModel):
    strategy: str
    target_tokens: int = Field(gt=0)
    overlap_tokens: int | None = Field(default=None, ge=0)
    message_overlap_count: int | None = Field(default=None, ge=0)
    comment_overlap_count: int | None = Field(default=None, ge=0)


class ChunkingConfig(BaseModel):
    version: str
    global_min_chunk_tokens: int = Field(gt=0)
    global_max_chunk_tokens: int = Field(gt=0)
    docs: SourceChunkingConfig
    slack_thread: SourceChunkingConfig
    linear_issue: SourceChunkingConfig
    github_pr: SourceChunkingConfig
    ocr: SourceChunkingConfig


class EmbeddingsConfig(BaseModel):
    version: str
    dev_provider: Literal["deterministic"]
    prod_provider: str
    prod_model: str
    prod_dimensions: int = Field(gt=0)
    batch_size: int = Field(gt=0)


class RetrievalConfig(BaseModel):
    version: str
    chunking: ChunkingConfig
    embeddings: EmbeddingsConfig
    candidate_retrieval: dict[str, int | str]
    ranking: dict[str, float | str]
    token_budget: dict[str, int | str] | None = None
    context_gate: dict[str, bool | float | int | str] | None = None


def load_retrieval_config(path: Path | None = None) -> RetrievalConfig:
    config_path = path or Path("config/retrieval-v1.yaml")
    return RetrievalConfig.model_validate(_parse_simple_yaml(config_path.read_text()))


def _parse_simple_yaml(content: str) -> dict[str, Any]:
    root: dict[str, Any] = {}
    stack: list[tuple[int, dict[str, Any]]] = [(-1, root)]
    for raw_line in content.splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        key, separator, value = raw_line.strip().partition(":")
        if not separator:
            raise ValueError(f"invalid YAML line: {raw_line}")
        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]
        if value.strip() == "":
            child: dict[str, Any] = {}
            parent[key] = child
            stack.append((indent, child))
        else:
            parent[key] = _parse_scalar(value.strip())
    return root


def _parse_scalar(value: str) -> int | float | str:
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        return value
