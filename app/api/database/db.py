#!/usr/bin/env python
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from core.config import settings

db_url = settings.TEST_DB_URL if settings.TESTING else settings.PROD_DB_URL
engine = create_async_engine(db_url, echo=False, pool_size=10)
async_session = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session
