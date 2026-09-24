"""Database engine construction and the readiness port."""

from typing import Any, Protocol
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

_CONNECT_TIMEOUT_S = 10
_COMMAND_TIMEOUT_S = 15
_POOL_TIMEOUT_S = 10


class DatabaseHealth(Protocol):
    async def ping(self) -> None: ...


def connect_args(*, require_ssl: bool) -> dict[str, Any]:
    """asyncpg connect arguments that are safe behind Supabase's transaction pooler."""
    args: dict[str, Any] = {
        "statement_cache_size": 0,
        "prepared_statement_name_func": lambda: f"__asyncpg_{uuid4()}__",
        "timeout": _CONNECT_TIMEOUT_S,
        "command_timeout": _COMMAND_TIMEOUT_S,
    }
    if require_ssl:
        # Encrypts and refuses a plaintext downgrade. It does not verify Supabase's certificate
        # chain (that needs their private CA bundle); enforce SSL on the Supabase side as well.
        args["ssl"] = "require"
    return args


def build_engine(database_url: str, *, require_ssl: bool = False) -> AsyncEngine:
    """Async engine for Supabase's transaction pooler (no prepared statements)."""
    url = make_url(database_url).update_query_dict({"prepared_statement_cache_size": "0"})
    return create_async_engine(
        url,
        pool_size=3,
        max_overflow=2,
        pool_timeout=_POOL_TIMEOUT_S,
        pool_recycle=1800,
        pool_pre_ping=True,
        hide_parameters=True,  # keep bound values (portfolio data) out of error output
        connect_args=connect_args(require_ssl=require_ssl),
    )


class SqlAlchemyHealth:
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def ping(self) -> None:
        async with self._engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
