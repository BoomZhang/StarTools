"""数据库与缓存连接的创建和释放，供应用生命周期及健康检查使用。"""

from collections.abc import AsyncIterator

import redis.asyncio as redis
from fastapi import Request
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings


def create_engine() -> AsyncEngine:
    return create_async_engine(settings.database_url, pool_pre_ping=True)


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


def create_redis() -> redis.Redis:
    return redis.from_url(settings.redis_url, decode_responses=True)


async def get_db(request: Request) -> AsyncIterator[AsyncSession]:
    factory: async_sessionmaker[AsyncSession] = request.app.state.db_session
    async with factory() as session:
        yield session
