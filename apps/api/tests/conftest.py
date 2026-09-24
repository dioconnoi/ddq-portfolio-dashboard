import asyncio
from collections.abc import Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient

from ddq_api.core.config import Settings
from ddq_api.main import create_app


class FakeDbHealth:
    def __init__(self, error: Exception | None = None, delay: float = 0.0) -> None:
        self._error = error
        self._delay = delay

    async def ping(self) -> None:
        if self._delay:
            await asyncio.sleep(self._delay)
        if self._error is not None:
            raise self._error


@pytest.fixture
def settings() -> Settings:
    return Settings(  # type: ignore[call-arg]
        _env_file=None,
        environment="test",
        database_url="postgresql://u:p@localhost:5432/db",
        allowed_origins="http://localhost:5173",
    )


@pytest.fixture
def make_client(settings: Settings) -> Callable[..., TestClient]:
    def _make(
        *, db_error: Exception | None = None, db_delay: float = 0.0, **overrides: Any
    ) -> TestClient:
        effective = settings.model_copy(update=overrides) if overrides else settings
        app = create_app(effective, db_health=FakeDbHealth(db_error, db_delay))
        return TestClient(app, raise_server_exceptions=False)

    return _make
