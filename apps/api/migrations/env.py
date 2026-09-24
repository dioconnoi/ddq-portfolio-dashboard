"""Alembic environment: async engine, URL from the environment (never from alembic.ini)."""

import asyncio
import os

from alembic import context
from sqlalchemy.engine import Connection

from ddq_api.core.config import normalize_database_url
from ddq_api.core.db import build_engine

target_metadata = None  # SQL-first migrations; no ORM metadata autogenerate


def _database_url() -> str:
    raw = os.environ.get("DDQ_DATABASE_MIGRATION_URL") or os.environ.get("DDQ_DATABASE_URL")
    if not raw:
        raise RuntimeError(
            "Set DDQ_DATABASE_MIGRATION_URL (preferred, session pooler) or DDQ_DATABASE_URL."
        )
    return normalize_database_url(raw)


def _run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def _run_online() -> None:
    engine = build_engine(_database_url())
    try:
        async with engine.connect() as connection:
            await connection.run_sync(_run_migrations)
    finally:
        await engine.dispose()


if context.is_offline_mode():
    raise RuntimeError("Offline (--sql) migrations are not supported; run against a database.")

asyncio.run(_run_online())
