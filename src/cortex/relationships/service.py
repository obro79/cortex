from __future__ import annotations

from dataclasses import dataclass

from cortex.contracts.entities import SourceObject
from cortex.ingestion.payloads import sha256_digest
from cortex.normalization.result import RelationshipSeed

from .parsers import DeterministicRelationshipParser, ParsedRelationshipHint

RELATIONSHIP_VERSION = "deterministic-relationships-v1"


@dataclass(frozen=True)
class RelationshipBuildResult:
    seeds: list[RelationshipSeed]
    unresolved_hints: list[ParsedRelationshipHint]


class DeterministicRelationshipBuilder:
    def __init__(self, parser: DeterministicRelationshipParser | None = None) -> None:
        self.parser = parser or DeterministicRelationshipParser()

    def build(
        self,
        *,
        workspace_id: str,
        source_objects: list[SourceObject],
        raw_event_id: str,
        trace_id: str | None = None,
    ) -> RelationshipBuildResult:
        by_key = _object_lookup(source_objects)
        seeds: list[RelationshipSeed] = []
        unresolved: list[ParsedRelationshipHint] = []
        for source_object in source_objects:
            for hint in self.parser.parse_text(source_object.content_text or ""):
                target_id = by_key.get(hint.target_key)
                if target_id is None or target_id == source_object.id:
                    unresolved.append(hint)
                    continue
                seeds.append(
                    RelationshipSeed(
                        id=_relationship_id(
                            workspace_id,
                            hint.relationship_type,
                            source_object.id,
                            target_id,
                        ),
                        workspace_id=workspace_id,
                        relationship_type=hint.relationship_type,
                        from_id=source_object.id,
                        to_id=target_id,
                        confidence=hint.confidence,
                        raw_event_id=raw_event_id,
                        normalized_version=RELATIONSHIP_VERSION,
                        trace_id=trace_id,
                    )
                )
        return RelationshipBuildResult(
            seeds=_dedupe(seeds), unresolved_hints=unresolved
        )


def _relationship_id(
    workspace_id: str, relationship_type: str, from_id: str, to_id: str
) -> str:
    digest = sha256_digest(
        "|".join(
            [workspace_id, relationship_type, from_id, to_id, RELATIONSHIP_VERSION]
        ).encode()
    ).removeprefix("sha256:")[:24]
    return f"rel_{digest}"


def _object_lookup(source_objects: list[SourceObject]) -> dict[str, str]:
    lookup = {}
    for source_object in source_objects:
        if source_object.provider == "linear":
            identifier = source_object.metadata_json.get("identifier")
            if isinstance(identifier, str):
                lookup[f"linear:{identifier}"] = source_object.id
        elif source_object.provider == "github":
            number = source_object.metadata_json.get("number")
            sha = source_object.metadata_json.get("sha")
            if source_object.object_type == "github_pull_request" and number:
                lookup[f"github:pr:{number}"] = source_object.id
            if source_object.object_type == "github_commit" and isinstance(sha, str):
                lookup[f"github:commit:{sha}"] = source_object.id
        elif source_object.provider == "repo_docs":
            path = source_object.metadata_json.get("path")
            if isinstance(path, str):
                lookup[f"doc:path:{path}"] = source_object.id
        elif source_object.provider == "slack" and source_object.canonical_url:
            lookup[f"slack:{source_object.canonical_url}"] = source_object.id
    return lookup


def _dedupe(seeds: list[RelationshipSeed]) -> list[RelationshipSeed]:
    seen = set()
    deduped = []
    for seed in seeds:
        key = (seed.relationship_type, seed.from_id, seed.to_id)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(seed)
    return deduped
