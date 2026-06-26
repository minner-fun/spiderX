"""调度 · 对账总览（M3）：调度时间线 + 队列水位 + 对账(已分发/未完成/DLQ)。"""
from __future__ import annotations
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from croniter import croniter

from shared.db import get_session
from shared.models import Schedule, Spider, Project, Run
from shared.redis_bus import get_async_redis
from shared.enums import RunExecStatus

router = APIRouter(prefix="/api/schedule", tags=["schedule"])

STUCK_AFTER = timedelta(minutes=10)
CELERY_QUEUE = "celery"  # M0/M3 默认队列；命名队列 default/high/retry/low 后续


@router.get("/overview")
async def overview(session: AsyncSession = Depends(get_session)):
    now = datetime.now(timezone.utc)
    day_ago = now - timedelta(hours=24)

    # —— 调度时间线 ——
    rows = (await session.execute(
        select(Schedule, Spider.name, Project.domain)
        .join(Spider, Schedule.spider_id == Spider.id)
        .join(Project, Spider.project_id == Project.id)
        .order_by(Schedule.enabled.desc())
    )).all()
    horizon = now + timedelta(hours=24)
    schedules = []
    for sched, name, domain in rows:
        next_run = None
        fires: list[float] = []  # 未来 24h 内的触发点（距 now 的小时偏移 0..24）
        try:
            it = croniter(sched.cron, now)
            nxt = it.get_next(datetime)
            next_run = nxt.isoformat()
            t = nxt
            while t <= horizon and len(fires) < 60:
                fires.append(round((t - now).total_seconds() / 3600, 3))
                t = it.get_next(datetime)
        except Exception:
            pass
        schedules.append({
            "spider_id": str(sched.spider_id), "spider_name": name, "domain": domain,
            "cron": sched.cron, "queue": sched.queue, "enabled": sched.enabled,
            "jitter_sec": sched.jitter_sec,
            "last_run_at": sched.last_run_at.isoformat() if sched.last_run_at else None,
            "next_run_at": next_run, "fires": fires,
        })

    # —— 对账（近 24h）——
    async def _count(*conds):
        return await session.scalar(select(func.count()).select_from(Run).where(*conds)) or 0

    running_states = [RunExecStatus.queued.value, RunExecStatus.running.value]
    dispatched = await _count(Run.created_at >= day_ago)
    started = await _count(Run.exec_status.in_(running_states))
    completed = await _count(Run.created_at >= day_ago, Run.finished_at.isnot(None))
    stuck = await _count(Run.exec_status.in_(running_states), Run.started_at < (now - STUCK_AFTER))
    failed = await _count(Run.created_at >= day_ago, Run.exec_status == RunExecStatus.failed.value)

    # —— 队列水位（Redis）——
    queues = []
    try:
        r = get_async_redis()
        depth = await r.llen(CELERY_QUEUE)
        await r.aclose()
    except Exception:
        depth = 0
    queues.append({"name": "default", "depth": depth})
    for nm in ("high", "retry", "low"):
        queues.append({"name": nm, "depth": 0})

    return {
        "schedules": schedules,
        "reconcile": {"dispatched": dispatched, "started": started, "completed": completed,
                      "stuck": stuck, "failed": failed, "dlq": 0},
        "queues": queues,
        "now": now.isoformat(),
    }
