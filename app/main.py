from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import Settings, get_settings
from app.core.exceptions import AppError, unhandled_exception_handler
from app.core.logging import configure_logging, get_logger
from app.db.session import DatabaseSessionManager

logger = get_logger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = settings or get_settings()
    configure_logging()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        session_manager = DatabaseSessionManager(app_settings.resolved_database_url)
        app.state.settings = app_settings
        app.state.session_manager = session_manager
        await session_manager.ping()
        logger.info("Database connection established")
        logger.info("Application started")
        try:
            yield
        finally:
            await session_manager.dispose()
            logger.info("Application stopped")

    app = FastAPI(title=app_settings.app_name, lifespan=lifespan)
    app.include_router(api_router)
    app.add_exception_handler(AppError, AppError.handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)

    return app


app = create_app()
