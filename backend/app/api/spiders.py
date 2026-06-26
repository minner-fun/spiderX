"""爬虫 M1 API：列表(筛选/分页) + 详情 + PATCH + 版本(列表/diff/回滚) + 运行 + 触发。"""
from __future__ import annotations
import uuid
import json
import difflib

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, case
from sqlalchemy.ext.asyncio import AsyncSession

from shared.db import get_session
from shared.models import Spider, Project, User, Run, Schedule, SpiderVersion
from shared.enums import RunExecStatus
from backend.app.schemas import (
    SpiderCreate, SpiderOut, SpiderPatch, SpiderListItem, SpiderListOut,
    SpiderDetailOut, VersionOut, RunOut, DiffOut, DiffLine, RollbackIn,
    RulesOut, RulesSaveIn,
)
from backend.app.core.celery_client import celery_producer

router = APIRouter(prefix="/api", tags=["spiders"])


# ——————————————————————————— 聚合辅助 ———————————————————————————

async def _agg_for(session: AsyncSession, spider_ids: list[uuid.UUID]) -> dict[uuid.UUID, dict]:
    """为一组 spider 计算展示聚合：cron / last_run_at / success_rate / current_version。"""
    if not spider_ids:
        return {}
    out: dict[uuid.UUID, dict] = {sid: {} for sid in spider_ids}

    # 调度 cron（取每 spider 一条）
    for sid, cron in (await session.execute(
        select(Schedule.spider_id, Schedule.cron).where(Schedule.spider_id.in_(spider_ids))
    )).all():
        out[sid].setdefault("cron", cron)

    # 运行聚合：总数 / 成功数 / 最近时间
    success = func.sum(case((Run.exec_status == RunExecStatus.success.value, 1), else_=0))
    rows = (await session.execute(
        select(Run.spider_id, func.count().label("n"), success.label("ok"),
               func.max(Run.created_at).label("last"))
        .where(Run.spider_id.in_(spider_ids)).group_by(Run.spider_id)
    )).all()
    for sid, n, ok, last in rows:
        out[sid]["last_run_at"] = last
        out[sid]["success_rate"] = (float(ok) / n) if n else None

    # 线上版本号
    for sid, ver in (await session.execute(
        select(SpiderVersion.spider_id, SpiderVersion.version)
        .where(SpiderVersion.spider_id.in_(spider_ids), SpiderVersion.is_live.is_(True))
    )).all():
        out[sid]["current_version"] = ver

    return out


async def _latest_signals(session: AsyncSession, spider_id: uuid.UUID) -> dict | None:
    row = await session.scalar(
        select(Run.signals).where(Run.spider_id == spider_id)
        .order_by(Run.created_at.desc()).limit(1)
    )
    return row


# ——————————————————————————— 列表 / 创建 ———————————————————————————

@router.get("/projects/{project_id}/spiders", response_model=SpiderListOut)
async def list_spiders(
    project_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    status: str | None = None,
    health: str | None = None,
    owner: str | None = None,
    domain: str | None = None,
    q: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    proj = await session.get(Project, project_id)
    if not proj:
        raise HTTPException(404, "project not found")

    base = (
        select(Spider, User.name, Project.domain)
        .join(Project, Spider.project_id == Project.id)
        .outerjoin(User, Spider.owner_id == User.id)
        .where(Spider.project_id == project_id)
    )
    if status:
        base = base.where(Spider.status == status)
    if health:
        base = base.where(Spider.health_status == health)
    if owner:
        base = base.where(User.name.ilike(f"%{owner}%"))
    if domain:
        base = base.where(Project.domain == domain)
    if q:
        base = base.where(Spider.name.ilike(f"%{q}%"))

    total = await session.scalar(
        select(func.count()).select_from(base.order_by(None).subquery())
    )

    ordered = base.order_by(
        Spider.is_core.desc(), Spider.contribution_pct.desc(), Spider.created_at.desc()
    ).offset((page - 1) * page_size).limit(page_size)
    result = (await session.execute(ordered)).all()

    spiders = [r[0] for r in result]
    agg = await _agg_for(session, [sp.id for sp in spiders])

    items = []
    for sp, owner_name, dom in result:
        a = agg.get(sp.id, {})
        items.append(SpiderListItem(
            id=sp.id, project_id=sp.project_id, name=sp.name, domain=dom,
            owner_name=owner_name, status=sp.status, health_status=sp.health_status,
            priority=sp.priority, contribution_pct=sp.contribution_pct, is_core=sp.is_core,
            cron=a.get("cron"), last_run_at=a.get("last_run_at"),
            success_rate=a.get("success_rate"), created_at=sp.created_at,
        ))
    return SpiderListOut(items=items, total=total or 0, page=page, page_size=page_size)


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


# ——————————————————————————— 详情 / PATCH ———————————————————————————

async def _detail(session: AsyncSession, spider_id: uuid.UUID) -> SpiderDetailOut:
    row = (await session.execute(
        select(Spider, User.name, Project.domain)
        .join(Project, Spider.project_id == Project.id)
        .outerjoin(User, Spider.owner_id == User.id)
        .where(Spider.id == spider_id)
    )).first()
    if not row:
        raise HTTPException(404, "spider not found")
    sp, owner_name, dom = row
    agg = (await _agg_for(session, [sp.id])).get(sp.id, {})
    signals = await _latest_signals(session, sp.id)
    return SpiderDetailOut(
        id=sp.id, project_id=sp.project_id, name=sp.name, domain=dom, owner_name=owner_name,
        status=sp.status, health_status=sp.health_status, priority=sp.priority,
        contribution_pct=sp.contribution_pct, is_core=sp.is_core, tags=sp.tags or [],
        cron=agg.get("cron"), current_version=agg.get("current_version"),
        last_run_at=agg.get("last_run_at"), success_rate=agg.get("success_rate"),
        signals=signals, created_at=sp.created_at,
    )


@router.get("/spiders/{spider_id}", response_model=SpiderDetailOut)
async def get_spider(spider_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    return await _detail(session, spider_id)


@router.patch("/spiders/{spider_id}", response_model=SpiderDetailOut)
async def patch_spider(
    spider_id: uuid.UUID, body: SpiderPatch, session: AsyncSession = Depends(get_session)
):
    spider = await session.get(Spider, spider_id)
    if not spider:
        raise HTTPException(404, "spider not found")
    if body.status is not None:
        spider.status = body.status
    if body.priority is not None:
        spider.priority = body.priority
    await session.commit()
    return await _detail(session, spider_id)


# ——————————————————————————— 版本 ———————————————————————————

@router.get("/spiders/{spider_id}/versions", response_model=list[VersionOut])
async def list_versions(spider_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    rows = (await session.execute(
        select(SpiderVersion, User.name)
        .outerjoin(User, SpiderVersion.author_id == User.id)
        .where(SpiderVersion.spider_id == spider_id)
        .order_by(SpiderVersion.version.desc())
    )).all()
    return [
        VersionOut(
            id=v.id, spider_id=v.spider_id, version=v.version, is_live=v.is_live,
            author_name=author, change_msg=v.change_msg, created_at=v.created_at,
        )
        for v, author in rows
    ]


async def _version_rules(session: AsyncSession, spider_id: uuid.UUID, n: int) -> dict:
    v = await session.scalar(
        select(SpiderVersion).where(
            SpiderVersion.spider_id == spider_id, SpiderVersion.version == n
        )
    )
    if not v:
        raise HTTPException(404, f"version {n} not found")
    return {"rules": v.rules, "incremental": v.incremental, "hooks": v.hooks}


@router.get("/spiders/{spider_id}/versions/diff", response_model=DiffOut)
async def diff_versions(
    spider_id: uuid.UUID,
    from_: int = Query(..., alias="from"),
    to: int = Query(...),
    session: AsyncSession = Depends(get_session),
):
    a = await _version_rules(session, spider_id, from_)
    b = await _version_rules(session, spider_id, to)
    a_txt = json.dumps(a, indent=2, ensure_ascii=False, sort_keys=True).splitlines()
    b_txt = json.dumps(b, indent=2, ensure_ascii=False, sort_keys=True).splitlines()

    lines: list[DiffLine] = []
    for d in difflib.ndiff(a_txt, b_txt):
        tag, text = d[:2], d[2:]
        if tag == "+ ":
            lines.append(DiffLine(op="add", text=text))
        elif tag == "- ":
            lines.append(DiffLine(op="del", text=text))
        elif tag == "  ":
            lines.append(DiffLine(op="ctx", text=text))
        # "? " 提示行跳过
    return DiffOut(from_=from_, to=to, lines=lines)


@router.get("/spiders/{spider_id}/rules", response_model=RulesOut)
async def get_rules(spider_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    """编辑器加载当前线上版本的完整配置（无线上版本则返回空规则）。"""
    v = await session.scalar(
        select(SpiderVersion).where(
            SpiderVersion.spider_id == spider_id, SpiderVersion.is_live.is_(True)
        )
    )
    if not v:
        v = await session.scalar(
            select(SpiderVersion).where(SpiderVersion.spider_id == spider_id)
            .order_by(SpiderVersion.version.desc()).limit(1)
        )
    if not v:
        return RulesOut(version=None, rules={}, incremental={}, hooks=[])
    return RulesOut(version=v.version, rules=v.rules or {},
                    incremental=v.incremental or {}, hooks=v.hooks or [])


@router.post("/spiders/{spider_id}/rules", response_model=VersionOut, status_code=201)
async def save_rules(
    spider_id: uuid.UUID, body: RulesSaveIn, session: AsyncSession = Depends(get_session)
):
    """保存并试运行：生成新版本并置为线上（配置即版本，禁止复制文件）。"""
    spider = await session.get(Spider, spider_id)
    if not spider:
        raise HTTPException(404, "spider not found")
    max_v = await session.scalar(
        select(func.max(SpiderVersion.version)).where(SpiderVersion.spider_id == spider_id)
    )
    for v in (await session.scalars(
        select(SpiderVersion).where(
            SpiderVersion.spider_id == spider_id, SpiderVersion.is_live.is_(True)
        )
    )).all():
        v.is_live = False

    new_ver = SpiderVersion(
        spider_id=spider_id, version=(max_v or 0) + 1,
        rules=body.rules, incremental=body.incremental, hooks=body.hooks,
        is_live=True, author_id=spider.owner_id,
        change_msg=body.change_msg or f"v{(max_v or 0) + 1} 规则编辑器保存",
    )
    session.add(new_ver)
    await session.flush()
    spider.current_version_id = new_ver.id
    await session.commit()
    await session.refresh(new_ver)
    author = await session.scalar(select(User.name).where(User.id == new_ver.author_id))
    return VersionOut(
        id=new_ver.id, spider_id=new_ver.spider_id, version=new_ver.version,
        is_live=new_ver.is_live, author_name=author, change_msg=new_ver.change_msg,
        created_at=new_ver.created_at,
    )


@router.post("/spiders/{spider_id}/rollback", response_model=VersionOut, status_code=201)
async def rollback(
    spider_id: uuid.UUID, body: RollbackIn, session: AsyncSession = Depends(get_session)
):
    """治理：回滚 = 复制目标版本配置为一个新版本并置为线上（禁止复制文件当版本）。"""
    target = await session.scalar(
        select(SpiderVersion).where(
            SpiderVersion.spider_id == spider_id, SpiderVersion.version == body.version
        )
    )
    if not target:
        raise HTTPException(404, f"version {body.version} not found")
    max_v = await session.scalar(
        select(func.max(SpiderVersion.version)).where(SpiderVersion.spider_id == spider_id)
    )
    # 取消旧线上
    for v in (await session.scalars(
        select(SpiderVersion).where(
            SpiderVersion.spider_id == spider_id, SpiderVersion.is_live.is_(True)
        )
    )).all():
        v.is_live = False

    new_ver = SpiderVersion(
        spider_id=spider_id, version=(max_v or 0) + 1,
        rules=target.rules, incremental=target.incremental, hooks=target.hooks,
        is_live=True, author_id=target.author_id,
        change_msg=f"↶ 回滚至 v{body.version}",
    )
    session.add(new_ver)
    await session.flush()
    spider = await session.get(Spider, spider_id)
    if spider:
        spider.current_version_id = new_ver.id
    await session.commit()
    await session.refresh(new_ver)
    author = await session.scalar(select(User.name).where(User.id == new_ver.author_id))
    return VersionOut(
        id=new_ver.id, spider_id=new_ver.spider_id, version=new_ver.version,
        is_live=new_ver.is_live, author_name=author, change_msg=new_ver.change_msg,
        created_at=new_ver.created_at,
    )


# ——————————————————————————— 运行 / 触发 ———————————————————————————

@router.get("/spiders/{spider_id}/runs", response_model=list[RunOut])
async def list_runs(
    spider_id: uuid.UUID, limit: int = Query(10, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    rows = await session.scalars(
        select(Run).where(Run.spider_id == spider_id)
        .order_by(Run.created_at.desc()).limit(limit)
    )
    return list(rows)


@router.post("/spiders/{spider_id}/run", status_code=202)
async def trigger_run(spider_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    spider = await session.get(Spider, spider_id)
    if not spider:
        raise HTTPException(404, "spider not found")
    celery_producer.send_task("worker.ping_run", args=[str(spider_id)])
    return {"queued": True, "spider_id": str(spider_id)}
