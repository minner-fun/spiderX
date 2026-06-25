"""Redis pub/sub 实时总线：worker 发、backend 订阅后经 WebSocket 推前端。"""
from __future__ import annotations
import json
import os
import redis.asyncio as aioredis
import redis as sync_redis


def _url() -> str:
    return os.getenv("REDIS_URL", "redis://redis:6379/0")


# 异步客户端（backend 用）
def get_async_redis() -> aioredis.Redis:
    return aioredis.from_url(_url(), decode_responses=True)


# 同步客户端（worker 用）
def get_sync_redis() -> sync_redis.Redis:
    return sync_redis.from_url(_url(), decode_responses=True)


def publish_sync(channel: str, payload: dict) -> None:
    r = get_sync_redis()
    try:
        r.publish(channel, json.dumps(payload, ensure_ascii=False, default=str))
    finally:
        r.close()
