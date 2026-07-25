from collections.abc import AsyncIterator

from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine as sa_create_async_engine


def normalize_asyncpg_url(database_url: str) -> str:
    url = make_url(database_url)
    if url.drivername != "postgresql+asyncpg":
        return database_url
    query = dict(url.query)
    if query.pop("sslmode", None) == "require":
        query["ssl"] = "require"
    query.pop("channel_binding", None)
    return url.set(query=query).render_as_string(hide_password=False)


def create_async_engine(database_url: str) -> AsyncEngine:
    if not database_url:
        raise ValueError("DATABASE_URL is required to create a database engine")
    return sa_create_async_engine(
        normalize_asyncpg_url(database_url), pool_pre_ping=True
    )


def create_sessionmaker(database_url: str) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(create_async_engine(database_url), expire_on_commit=False)


async def session_scope(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    async with session_factory() as session:
        yield session
