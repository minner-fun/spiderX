"""共享 DB 层：async engine/session（运行时用）+ sync URL（alembic 用）。
shared 保持依赖轻量，直接读环境变量，不耦合 backend 的 Settings。"""
from __future__ import annotations
import os
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine, AsyncSession
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session


class Base(DeclarativeBase):
    pass


def _async_url() -> str:
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL 未设置")
    return url


def sync_url() -> str:
    return os.getenv("DATABASE_URL_SYNC") or _async_url().replace("+asyncpg", "+psycopg")


engine = create_async_engine(_async_url(), pool_pre_ping=True, future=True)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_session() -> AsyncSession:
    """FastAPI 依赖：每请求一个 async session。"""
    async with async_session_maker() as session:
        yield session


# 同步 session（Celery worker 用，worker 任务是同步执行）
sync_engine = create_engine(sync_url(), pool_pre_ping=True, future=True)
sync_session_maker = sessionmaker(sync_engine, expire_on_commit=False, class_=Session)
