import pytest
from sqlalchemy.exc import SQLAlchemyError

from ddq_api.core.db import SqlAlchemyHealth, build_engine, connect_args

URL = "postgresql+asyncpg://u:p@127.0.0.1:1/db"


def test_engine_disables_prepared_statement_cache_for_the_pooler() -> None:
    engine = build_engine(URL)
    assert engine.url.query["prepared_statement_cache_size"] == "0"


def test_engine_hides_sql_parameters_from_error_output() -> None:
    assert build_engine(URL).sync_engine.hide_parameters is True


def test_connect_args_disable_the_statement_cache_and_set_timeouts() -> None:
    args = connect_args(require_ssl=False)
    assert args["statement_cache_size"] == 0
    assert args["prepared_statement_name_func"]().startswith("__asyncpg_")
    assert 0 < args["timeout"] <= 15
    assert 0 < args["command_timeout"] <= 30
    assert "ssl" not in args


def test_connect_args_require_tls_when_asked() -> None:
    assert connect_args(require_ssl=True)["ssl"] == "require"


async def test_ping_raises_when_database_unreachable() -> None:
    engine = build_engine(URL)
    try:
        with pytest.raises((OSError, SQLAlchemyError)):
            await SqlAlchemyHealth(engine).ping()
    finally:
        await engine.dispose()
