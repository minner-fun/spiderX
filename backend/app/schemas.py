"""Pydantic 出入参（M0 最小集）。"""
from __future__ import annotations
import uuid
from datetime import datetime
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


class RunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    spider_id: uuid.UUID
    exec_status: str
    data_outcome: str
    signals: dict
    created_at: datetime
