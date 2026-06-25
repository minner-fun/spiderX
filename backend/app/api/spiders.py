"""爬虫最小 CRUD + 触发一次 run（M0 验证主链路）。"""
from __future__ import annotations
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.db import get_session
from shared.models import Spider, Project
from backend.app.schemas import SpiderCreate, SpiderOut
from backend.app.core.celery_client import celery_producer

router = APIRouter(prefix="/api", tags=["spiders"])


@router.get("/projects/{project_id}/spiders", response_model=list[SpiderOut])
async def list_spiders(project_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    rows = await session.scalars(
        select(Spider).where(Spider.project_id == project_id).order_by(Spider.created_at.desc())
    )
    return list(rows)


@router.post("/projects/{project_id}/spiders", response_model=SpiderOut, status_code=201)
async def create_spider(
    project_id: uuid.UUID, body: SpiderCreate, session: AsyncSession = Depends(get_session)
):
    proj = await session.get(Project, project_id)
    if not proj:
        raise HTTPException(404, "project not found")
    spider = Spider(
        project_id=project_id, name=body.name, owner_id=body.owner_id,
        priority=body.priority, tags=body.tags,
    )
    session.add(spider)
    await session.commit()
    await session.refresh(spider)
    return spider


@router.post("/spiders/{spider_id}/run", status_code=202)
async def trigger_run(spider_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    """M0 终验：触发 worker 写一条 Run + 实时推送（不做真实抓取）。"""
    spider = await session.get(Spider, spider_id)
    if not spider:
        raise HTTPException(404, "spider not found")
    celery_producer.send_task("worker.ping_run", args=[str(spider_id)])
    return {"queued": True, "spider_id": str(spider_id)}
