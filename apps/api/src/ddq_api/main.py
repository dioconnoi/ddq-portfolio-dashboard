"""ASGI application factory. Run: uvicorn ddq_api.main:create_app --factory"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from ddq_api import __version__
from ddq_api.core.config import Settings, get_settings
from ddq_api.core.db import DatabaseHealth, SqlAlchemyHealth, build_engine
from ddq_api.core.handlers import register_exception_handlers
from ddq_api.core.logging import configure_logging
from ddq_api.core.middleware import install_middleware
from ddq_api.routers import health


def create_app(
    settings: Settings | None = None, *, db_health: DatabaseHealth | None = None
) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        engine = None
        if db_health is None:
            engine = build_engine(
                settings.database_url.get_secret_value(),
                require_ssl=settings.environment == "production",
            )
            app.state.db_health = SqlAlchemyHealth(engine)
        try:
            yield
        finally:
            if engine is not None:
                await engine.dispose()

    app = FastAPI(title="DDQ Portfolio Dashboard API", version=__version__, lifespan=lifespan)
    app.state.settings = settings
    if db_health is not None:
        app.state.db_health = db_health

    register_exception_handlers(app)
    install_middleware(app, settings)
    app.include_router(health.router)
    return app
