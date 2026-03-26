from __future__ import annotations

import asyncio

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.db.session import DatabaseSessionManager

logger = get_logger(__name__)


async def main() -> None:
    configure_logging()
    settings = get_settings()
    session_manager = DatabaseSessionManager(settings.resolved_database_url)

    try:
        for attempt in range(1, 11):
            try:
                await session_manager.ping()
                logger.info("Database is ready")
                return
            except Exception as exc:  # pragma: no cover
                if attempt == 10:
                    raise exc
                logger.warning("Database is not ready yet, attempt %s/10", attempt)
                await asyncio.sleep(2)
    finally:
        await session_manager.dispose()


if __name__ == "__main__":
    asyncio.run(main())

