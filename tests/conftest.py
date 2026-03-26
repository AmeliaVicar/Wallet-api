from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator
from pathlib import Path
from uuid import UUID

import pytest
from alembic import command
from alembic.config import Config
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, text
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from app.core.config import Settings, get_settings
from app.db.models.wallet import Wallet
from app.main import create_app

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def get_test_database_url() -> str:
    return os.getenv(
        "TEST_DATABASE_URL",
        os.getenv(
            "DATABASE_URL",
            "postgresql+asyncpg://postgres:postgres@localhost:5432/wallets_test",
        ),
    )


def build_alembic_config(database_url: str) -> Config:
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(PROJECT_ROOT / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def run_migrations(database_url: str, revision: str) -> None:
    previous_database_url = os.environ.get("DATABASE_URL")

    try:
        os.environ["DATABASE_URL"] = database_url
        get_settings.cache_clear()
        config = build_alembic_config(database_url)
        command.upgrade(config, revision)
    finally:
        if previous_database_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous_database_url
        get_settings.cache_clear()


async def reset_public_tables(engine: AsyncEngine) -> None:
    async with engine.begin() as connection:
        result = await connection.execute(
            text(
                "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename"
            )
        )
        table_names = [row[0] for row in result]
        for table_name in table_names:
            safe_table_name = table_name.replace('"', '""')
            await connection.execute(
                text(f'DROP TABLE IF EXISTS "{safe_table_name}" CASCADE')
            )


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    return Settings(database_url=get_test_database_url())


@pytest.fixture(scope="session")
async def engine(test_settings: Settings) -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(test_settings.resolved_database_url, pool_pre_ping=True)

    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))

        await reset_public_tables(engine)
        await asyncio.to_thread(run_migrations, test_settings.resolved_database_url, "head")
    except Exception as exc:
        await engine.dispose()
        pytest.fail(f"PostgreSQL test database is not available or migrations failed: {exc}")

    yield engine

    await reset_public_tables(engine)
    await engine.dispose()


@pytest.fixture(scope="session")
def session_factory(engine: AsyncEngine) -> async_sessionmaker:
    return async_sessionmaker(bind=engine, expire_on_commit=False)


@pytest.fixture
async def app(engine: AsyncEngine, test_settings: Settings):
    return create_app(test_settings)


@pytest.fixture
async def client(app) -> AsyncIterator[AsyncClient]:
    async with LifespanManager(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as async_client:
            yield async_client


@pytest.fixture(autouse=True)
async def clean_wallets(session_factory: async_sessionmaker) -> AsyncIterator[None]:
    async with session_factory() as session:
        await session.execute(delete(Wallet))
        await session.commit()

    yield


@pytest.fixture
def wallet_factory(session_factory: async_sessionmaker):
    async def factory(balance: int = 0, wallet_id: UUID | None = None) -> Wallet:
        wallet = Wallet(balance=balance)
        if wallet_id is not None:
            wallet.id = wallet_id
        async with session_factory() as session:
            session.add(wallet)
            await session.commit()
            await session.refresh(wallet)
        return wallet

    return factory
