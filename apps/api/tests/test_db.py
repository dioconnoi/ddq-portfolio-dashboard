import pytest
from sqlalchemy.exc import SQLAlchemyError

from ddq_api.core.db import SqlAlchemyHealth, build_engine

URL = "postgresql+asyncpg://u:p@127.0.0.1:1/db"


def test_engine_disables_prepared_statement_cache_for_the_pooler() -> None:
    engine = build_engine(URL)
    assert engine.url.query["prepared_statement_cache_size"] == "0"


async def test_ping_raises_when_database_unreachable() -> None:
    engine = build_engine(URL)
    try:
        with pytest.raises((OSError, SQLAlchemyError)):
            await SqlAlchemyHealth(engine).ping()
    finally:
        await engine.dispose()
