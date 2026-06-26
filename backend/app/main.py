"""FastAPI 入口：/health + 爬虫 CRUD + WebSocket 实时（订阅 Redis → 推前端）。"""
from __future__ import annotations
import asyncio
import contextlib

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from shared.db import engine, async_session_maker
from shared.redis_bus import get_async_redis
from shared.enums import CH_TRIAGE
from backend.app.api import spiders, projects, engine as engine_api, schedule
from backend.app.seed import seed_demo

app = FastAPI(title="SpiderX API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)

app.include_router(projects.router)
app.include_router(spiders.router)
app.include_router(engine_api.router)
app.include_router(schedule.router)


@app.on_event("startup")
async def seed_defaults():
    """幂等 demo seed（空库时插入多域多健康态数据，撑 M1 屏）。"""
    async with async_session_maker() as s:
        await seed_demo(s)


@app.get("/health")
async def health():
    db_ok = redis_ok = False
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False
    try:
        r = get_async_redis()
        await r.ping()
        await r.aclose()
        redis_ok = True
    except Exception:
        redis_ok = False
    return {"status": "ok" if db_ok and redis_ok else "degraded", "db": db_ok, "redis": redis_ok}


@app.websocket("/ws/triage")
async def ws_triage(ws: WebSocket):
    """订阅 Redis CH_TRIAGE，转发给前端。M0 验证实时链路：worker 发 → 这里推。"""
    await ws.accept()
    r = get_async_redis()
    pubsub = r.pubsub()
    await pubsub.subscribe(CH_TRIAGE)
    try:
        while True:
            msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if msg and msg.get("data"):
                await ws.send_text(msg["data"])
            await asyncio.sleep(0.05)
    except WebSocketDisconnect:
        pass
    finally:
        with contextlib.suppress(Exception):
            await pubsub.unsubscribe(CH_TRIAGE)
            await pubsub.aclose()
            await r.aclose()
