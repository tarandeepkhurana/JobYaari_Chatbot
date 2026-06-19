# src/db/client.py

from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
)
from sqlalchemy import text

from src.config import settings


# ---------------------------------------------------------
# ENGINES
# ---------------------------------------------------------

ASYNC_PGBOUNCER_CONNECT_ARGS = {
    "statement_cache_size": 0,
}

# Write engine
write_engine = create_async_engine(
    settings.DIRECT_URL,
    pool_pre_ping=True,
    connect_args=ASYNC_PGBOUNCER_CONNECT_ARGS,
)

# Read engine
read_engine = create_async_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    connect_args=ASYNC_PGBOUNCER_CONNECT_ARGS,
)


# ---------------------------------------------------------
# SESSION FACTORIES
# ---------------------------------------------------------

WriteSessionLocal = async_sessionmaker(
    bind=write_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

ReadSessionLocal = async_sessionmaker(
    bind=read_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ---------------------------------------------------------
# WRITE SESSION
# ---------------------------------------------------------

@asynccontextmanager
async def get_write_session():

    async with WriteSessionLocal() as session:

        try:
            yield session

            await session.commit()

        except Exception:

            await session.rollback()

            raise


# ---------------------------------------------------------
# READ SESSION
# ---------------------------------------------------------

@asynccontextmanager
async def get_read_session():

    async with ReadSessionLocal() as session:

        yield session


async def ping_database() -> None:
    """Verify DB connectivity during application startup."""

    async with read_engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
