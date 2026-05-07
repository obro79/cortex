from __future__ import annotations

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

    @property
    def id(self) -> str:
        return self.source_chunk.id


@dataclass(frozen=True)
class RetrievalCandidates:
    candidates: list[Candidate]
    errors: dict[str, str] = field(default_factory=dict)
