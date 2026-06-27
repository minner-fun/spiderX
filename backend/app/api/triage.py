"""巡检分诊（M4）：三态计数 + 核心站盯梢 + 全量热力图 + 分诊队列 + 🟡 snooze 闭环。
跨项目舰队视图（纲要 §5）。健康由最近 Run 的四层信号驱动（M3 真实产出）。"""
from __future__ import annotations
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from shared.db import get_session
from shared.models import Spider, Project, Run, SnoozeState, User
from shared.enums import HealthStatus

router = APIRouter(prefix="/api/triage", tags=["triage"])

# 健康态排序权重（红前黄中绿后）+ 价值权重
_HEALTH_ORDER = {"structural_fail": 0, "data_dry": 1, "unknown": 2, "healthy": 3}
_PRIO_RANK = {"P0": 3, "P1": 2, "P2": 1}


async def _run_stats(session: AsyncSession, ids: list[uuid.UUID], points: int = 12) -> dict:
    """批量取各 spider 近期 dedup_new 序列 → {sid: {today, baseline, spark}}。"""
    if not ids:
        return {}
    rows = (await session.execute(
        select(Run.spider_id, Run.signals, Run.created_at)
        .where(Run.spider_id.in_(ids)).order_by(Run.created_at.desc())
    )).all()
    by: dict[uuid.UUID, list] = {}
    for sid, signals, _ in rows:
        by.setdefault(sid, []).append((signals or {}).get("dedup_new"))
    out = {}
    for sid in ids:
        seq = by.get(sid, [])[:points]          # 近 → 远
        nums = [v for v in seq if isinstance(v, (int, float))]
        today = seq[0] if seq else None
        baseline = round(sum(nums[1:]) / len(nums[1:]), 1) if len(nums) > 1 else (nums[0] if nums else 0)
        out[sid] = {
            "today": today,
            "baseline": baseline,
            "spark": list(reversed([v if isinstance(v, (int, float)) else 0 for v in seq])),
        }
    return out


def _value(sp: Spider) -> float:
    return max(_PRIO_RANK.get(sp.priority, 1) * 10, sp.contribution_pct)


@router.get("/summary")
async def summary(session: AsyncSession = Depends(get_session)):
    rows = (await session.execute(
        select(Spider.health_status, func.count()).group_by(Spider.health_status)
    )).all()
    counts = {"structural_fail": 0, "data_dry": 0, "healthy": 0, "unknown": 0}
    for h, c in rows:
        counts[h] = c
    total = sum(counts.values())
    last = await session.scalar(select(func.max(Run.created_at)))
    return {"counts": counts, "total": total,
            "last_inspection": last.isoformat() if last else None}


@router.get("/heatmap")
async def heatmap(session: AsyncSession = Depends(get_session)):
    """全量站点健康格（红前黄中绿后，按价值次级排序）。"""
    rows = (await session.execute(
        select(Spider.id, Spider.name, Spider.health_status, Spider.priority,
               Spider.contribution_pct, Spider.is_core)
    )).all()
    cells = [{
        "id": str(r.id), "name": r.name, "health": r.health_status,
        "value": max(_PRIO_RANK.get(r.priority, 1) * 10, r.contribution_pct), "core": r.is_core,
    } for r in rows]
    cells.sort(key=lambda c: (_HEALTH_ORDER.get(c["health"], 9), -c["value"]))
    return {"cells": cells, "total": len(cells)}


@router.get("/core-sites")
async def core_sites(limit: int = Query(12, ge=1, le=40), session: AsyncSession = Depends(get_session)):
    """核心站盯梢：~20 站贡献 80% 数据，干涸最致命。按 is_core/价值取 Top。"""
    rows = (await session.execute(
        select(Spider).where(Spider.is_core.is_(True))
        .order_by(Spider.contribution_pct.desc()).limit(limit)
    )).all()
    spiders = [r[0] for r in rows]
    if len(spiders) < limit:
        more = (await session.execute(
            select(Spider).where(Spider.is_core.is_(False))
            .order_by(Spider.contribution_pct.desc()).limit(limit - len(spiders))
        )).all()
        spiders += [r[0] for r in more]
    stats = await _run_stats(session, [s.id for s in spiders])
    return {"sites": [{
        "id": str(s.id), "name": s.name, "health": s.health_status, "priority": s.priority,
        "contribution_pct": s.contribution_pct, "is_core": s.is_core,
        **stats.get(s.id, {"today": None, "baseline": 0, "spark": []}),
    } for s in spiders]}


def _signal_text(h: str) -> str:
    return {
        "structural_fail": "HTTP/列表层异常 → 改版结构故障，需改配置",
        "data_dry": "前三层正常但去重后新增=0 → 真没数据，待确认",
        "unknown": "关键层未上报（代码驱动未按契约回报）",
        "healthy": "四层信号正常，持续出数据",
    }.get(h, "")


@router.get("/queue")
async def queue(
    filter: str = Query("pending", pattern="^(pending|snoozed|escalated)$"),
    session: AsyncSession = Depends(get_session),
):
    now = datetime.now(timezone.utc)
    snoozes = {sn.spider_id: sn for sn in (await session.scalars(select(SnoozeState))).all()}

    def active_snooze(sid):
        sn = snoozes.get(sid)
        if not sn or sn.status == "released":
            return None
        if sn.status == "snoozed" and sn.snooze_until and sn.snooze_until < now:
            return None  # 到期视为解除
        return sn

    rows = (await session.execute(
        select(Spider, Project.domain).join(Project, Spider.project_id == Project.id)
    )).all()
    items = []
    for sp, domain in rows:
        sn = active_snooze(sp.id)
        if filter == "snoozed":
            if not sn or sn.status != "snoozed":
                continue
        elif filter == "escalated":
            if not sn or sn.status != "escalated":
                continue
        else:  # pending：非健康 且 无活动 snooze/escalate
            if sp.health_status == HealthStatus.healthy.value or sn:
                continue
        items.append((sp, domain, sn))

    # 按 健康严重度 × 价值 排序
    items.sort(key=lambda t: (_HEALTH_ORDER.get(t[0].health_status, 9), -_value(t[0])))
    stats = await _run_stats(session, [sp.id for sp, _, _ in items])
    return {"filter": filter, "items": [{
        "id": str(sp.id), "name": sp.name, "domain": domain, "health": sp.health_status,
        "priority": sp.priority, "contribution_pct": sp.contribution_pct, "is_core": sp.is_core,
        "signal_text": _signal_text(sp.health_status),
        "snooze_until": sn.snooze_until.isoformat() if sn and sn.snooze_until else None,
        "snooze_status": sn.status if sn else None,
        **stats.get(sp.id, {"today": None, "baseline": 0, "spark": []}),
    } for sp, domain, sn in items]}


class SnoozeIn(BaseModel):
    spider_id: uuid.UUID
    days: int = 3
    reason: str = "人工确认真没数据"


async def _upsert_snooze(session, spider_id, status, days, reason, baseline):
    sn = await session.scalar(select(SnoozeState).where(SnoozeState.spider_id == spider_id))
    until = datetime.now(timezone.utc).replace(microsecond=0)
    from datetime import timedelta
    until = until + timedelta(days=days) if status == "snoozed" else None
    if sn:
        sn.status, sn.reason, sn.snooze_until, sn.baseline = status, reason, until, baseline
    else:
        sn = SnoozeState(spider_id=spider_id, status=status, reason=reason,
                         snooze_until=until, baseline=baseline)
        session.add(sn)
    await session.commit()
    return sn


@router.post("/snooze")
async def snooze(body: SnoozeIn, session: AsyncSession = Depends(get_session)):
    sp = await session.get(Spider, body.spider_id)
    if not sp:
        raise HTTPException(404, "spider not found")
    sn = await _upsert_snooze(session, body.spider_id, "snoozed", body.days, body.reason, 0)
    return {"ok": True, "status": sn.status, "snooze_until": sn.snooze_until.isoformat() if sn.snooze_until else None}


class EscalateIn(BaseModel):
    spider_id: uuid.UUID
    reason: str = "人工升级为故障"


@router.post("/escalate")
async def escalate(body: EscalateIn, session: AsyncSession = Depends(get_session)):
    sp = await session.get(Spider, body.spider_id)
    if not sp:
        raise HTTPException(404, "spider not found")
    sp.priority = "P0"  # 升级 → 提到最高价值盯梢
    sn = await _upsert_snooze(session, body.spider_id, "escalated", 0, body.reason, 0)
    return {"ok": True, "status": sn.status}
