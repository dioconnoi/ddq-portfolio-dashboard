"""Database engine construction and the readiness port."""

from typing import Protocol
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine


class DatabaseHealth(Protocol):
    async def ping(self) -> None: ...


def build_engine(database_url: str) -> AsyncEngine:
    """Async engine that is safe behind Supabase's transaction pooler (no prepared statements)."""
    url = make_url(database_url).update_query_dict({"prepared_statement_cache_size": "0"})
    return create_async_engine(
        url,
        pool_size=3,
        max_overflow=2,
        pool_recycle=1800,
        pool_pre_ping=True,
        connect_args={
            "statement_cache_size": 0,
            "prepared_statement_name_func": lambda: f"__asyncpg_{uuid4()}__",
        },
    )


class SqlAlchemyHealth:
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def ping(self) -> None:
        async with self._engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
