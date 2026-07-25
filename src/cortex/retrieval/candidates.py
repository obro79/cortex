from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from cortex.contracts.entities import SourceChunk


@dataclass(frozen=True)
class Candidate:
    source_chunk: SourceChunk
    lexical_score: float = 0
    vector_score: float = 0
    relationship_score: float = 0
    source_authority_score: float = 0
    paths: set[str] = field(default_factory=set)
    score_provenance: Mapping[str, float] = field(default_factory=dict)

    @property
    def id(self) -> str:
        return self.source_chunk.id


@dataclass(frozen=True)
class RetrievalCandidates:
    candidates: list[Candidate]
    errors: dict[str, str] = field(default_factory=dict)
