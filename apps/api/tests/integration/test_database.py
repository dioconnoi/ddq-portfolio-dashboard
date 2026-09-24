import asyncio
import os
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import text

from ddq_api.core.config import normalize_database_url
from ddq_api.core.db import SqlAlchemyHealth, build_engine

pytestmark = pytest.mark.integration

API_DIR = Path(__file__).resolve().parents[2]

# Every table in `public` must have row-level security on: the Supabase REST API exposes
# `public`, and our authorization lives in the FastAPI service layer, not in Postgres roles.
UNPROTECTED_TABLES_SQL = """
SELECT c.relname
FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public' AND c.relkind IN ('r', 'p') AND NOT c.relrowsecurity
ORDER BY c.relname
"""


def _alembic(url: str, *args: str) -> None:
    subprocess.run(  # noqa: S603  (fixed argv, no shell)
        [sys.executable, "-m", "alembic", "-c", str(API_DIR / "alembic.ini"), *args],
        cwd=API_DIR,
        env={**os.environ, "DDQ_DATABASE_MIGRATION_URL": url},
        capture_output=True,
        text=True,
        check=True,
    )


async def test_ping_succeeds_against_real_postgres(database_url: str) -> None:
    engine = build_engine(normalize_database_url(database_url))
    try:
        await SqlAlchemyHealth(engine).ping()
    finally:
        await engine.dispose()


async def test_baseline_migration_applies_and_every_table_has_rls(database_url: str) -> None:
    await asyncio.to_thread(_alembic, database_url, "upgrade", "head")
    engine = build_engine(normalize_database_url(database_url))
    try:
        async with engine.connect() as connection:
            version = (
                await connection.execute(text("SELECT version_num FROM alembic_version"))
            ).scalar_one()
            unprotected = (await connection.execute(text(UNPROTECTED_TABLES_SQL))).scalars().all()
    finally:
        await engine.dispose()
        await asyncio.to_thread(_alembic, database_url, "downgrade", "base")
    assert version == "0001"
    assert unprotected == [], f"tables without row-level security: {unprotected}"
