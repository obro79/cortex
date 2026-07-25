from __future__ import annotations

from pydantic import Field

from cortex.contracts.entities import EntityModel, SourceFile, SourceObject


class RelationshipSeed(EntityModel):
    id: str
    workspace_id: str
    relationship_type: str
    from_id: str
    to_id: str
    confidence: float = Field(ge=0, le=1)
    raw_event_id: str
    normalized_version: str
    trace_id: str | None = None


class NormalizationResult(EntityModel):
    raw_event_id: str
    normalized_version: str
    source_objects: list[SourceObject] = Field(default_factory=list)
    source_files: list[SourceFile] = Field(default_factory=list)
    relationship_seeds: list[RelationshipSeed] = Field(default_factory=list)
    skipped_reason: str | None = None
