"""项目列表（M0：前端拿到默认 project_id 即可建爬虫）。"""
from __future__ import annotations
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.db import get_session
from shared.models import Project
from backend.app.schemas import ProjectOut

router = APIRouter(prefix="/api", tags=["projects"])


@router.get("/projects", response_model=list[ProjectOut])
async def list_projects(session: AsyncSession = Depends(get_session)):
    rows = await session.scalars(select(Project).order_by(Project.created_at))
    return list(rows)
