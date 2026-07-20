from sqlalchemy.dialects import postgresql

from cortex.chunking.repositories import SqlAlchemySourceChunkRepository
from cortex.contracts.enums import SourceChunkStatus


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
        limit=5,
    )

    assert matches == []
    assert session.statement is not None
    compiled = str(session.statement.compile(dialect=postgresql.dialect()))  # type: ignore[union-attr]
    assert "to_tsvector" in compiled
    assert "websearch_to_tsquery" in compiled
    assert "ts_rank_cd" in compiled
    assert " @@ " in compiled
    assert "ILIKE" not in compiled
    assert "session" not in compiled
