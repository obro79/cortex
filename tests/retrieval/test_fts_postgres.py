from sqlalchemy.dialects import postgresql

from cortex.chunking.config import load_retrieval_config
from cortex.chunking.repositories import (
    InMemorySourceChunkRepository,
    SqlAlchemySourceChunkRepository,
)
from cortex.chunking.source_aware import SourceAwareChunker
from cortex.contracts.enums import SourceChunkStatus
from cortex.retrieval.fts import FtsRetriever
from cortex.retrieval.query import QueryPlanner


class _EmptyResult:
    def tuples(self) -> list[tuple[object, float]]:
        return []


class _RecordingSession:
    def __init__(self) -> None:
        self.statement: object | None = None

    async def execute(self, statement: object) -> _EmptyResult:
        self.statement = statement
        return _EmptyResult()


async def test_postgres_fts_uses_ranked_parameterized_tsvector_query() -> None:
    session = _RecordingSession()
    repository = SqlAlchemySourceChunkRepository(session)  # type: ignore[arg-type]

    matches = await repository.search_fts_ranked(
        workspace_id="ws_1",
        query='session "read path"',
        status=SourceChunkStatus.ACTIVE,
        chunking_version="chunking-v1",
        source_allowlist=["so_allowed"],
        provider_filters=["github"],
        limit=5,
    )

    assert matches == []
    assert session.statement is not None
    compiled = str(session.statement.compile(dialect=postgresql.dialect()))  # type: ignore[union-attr]
    assert "to_tsvector" in compiled
    assert "websearch_to_tsquery" in compiled
    assert "ts_rank_cd" in compiled
    assert " @@ " in compiled
    assert "JOIN source_objects" in compiled
    assert "source_chunks.source_object_id IN" in compiled
    assert "lower(source_objects.provider) IN" in compiled
    assert compiled.index("WHERE") < compiled.index("LIMIT")
    assert "ILIKE" not in compiled
    assert "session" not in compiled


async def test_fts_filters_candidates_before_its_limit(phase4_source_object) -> None:
    config = load_retrieval_config()
    chunker = SourceAwareChunker(config.chunking)
    base = chunker.chunks_for_source_object(phase4_source_object)[0]
    disallowed = base.model_copy(
        update={
            "id": "chunk_disallowed",
            "source_object_id": "so_disallowed",
            "text": "session session session reads",
            "metadata_json": {"provider": "slack"},
        }
    )
    allowed = base.model_copy(
        update={
            "id": "chunk_allowed",
            "source_object_id": "so_allowed",
            "text": "session reads",
            "metadata_json": {"provider": "github"},
        }
    )
    repository = InMemorySourceChunkRepository()
    repository.upsert_many([disallowed, allowed])

    candidates = await FtsRetriever(repository).retrieve(
        workspace_id="ws_1",
        plan=QueryPlanner().plan(
            query="session reads",
            source_allowlist=["so_allowed"],
            provider_filters=["github"],
        ),
        chunking_version=config.chunking.version,
        limit=1,
    )

    assert [candidate.id for candidate in candidates] == ["chunk_allowed"]
