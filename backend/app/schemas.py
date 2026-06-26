"""Pydantic 出入参。M1：列表(筛选/分页) + 详情 + 版本 + 运行。"""
from __future__ import annotations
import uuid
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    env: str
    domain: str


class SpiderCreate(BaseModel):
    name: str
    owner_id: uuid.UUID | None = None
    priority: str = "P2"
    tags: list[str] = []


class SpiderOut(BaseModel):
    """创建返回（最小集）。"""
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    status: str
    health_status: str
    priority: str
    contribution_pct: float
    is_core: bool
    created_at: datetime


class SpiderPatch(BaseModel):
    """M1：改执行态 / 业务价值。"""
    status: str | None = None
    priority: str | None = None


# —— 列表行（含 join 出来的展示字段）——
class SpiderListItem(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    domain: str
    owner_name: str | None = None
    status: str
    health_status: str
    priority: str
    contribution_pct: float
    is_core: bool
    cron: str | None = None
    last_run_at: datetime | None = None
    success_rate: float | None = None
    created_at: datetime


class SpiderListOut(BaseModel):
    items: list[SpiderListItem]
    total: int
    page: int
    page_size: int


# —— 详情 ——
class Signals(BaseModel):
    http_status: int | None = None
    list_rows: int | None = None
    field_fill_rate: float | None = None
    dedup_new: int | None = None
    duplicate: int | None = None
    missing_rate: float | None = None
    watermark_hit: bool | None = None


class SpiderDetailOut(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    domain: str
    owner_name: str | None = None
    status: str
    health_status: str
    priority: str
    contribution_pct: float
    is_core: bool
    tags: list[str] = []
    cron: str | None = None
    current_version: int | None = None
    last_run_at: datetime | None = None
    success_rate: float | None = None
    signals: Signals | None = None  # 最近一条 Run 的四层信号
    created_at: datetime


class VersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    spider_id: uuid.UUID
    version: int
    is_live: bool
    author_name: str | None = None
    change_msg: str
    created_at: datetime


class RunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    spider_id: uuid.UUID
    exec_status: str
    data_outcome: str
    signals: dict
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime


class DiffLine(BaseModel):
    op: Literal["add", "del", "chg", "ctx"]
    text: str


class DiffOut(BaseModel):
    from_: int
    to: int
    lines: list[DiffLine]
    model_config = ConfigDict(populate_by_name=True)


class RollbackIn(BaseModel):
    version: int
