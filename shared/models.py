"""SpiderX 首版数据模型（M0 七表）。被 backend 与 worker 共同导入。
硬约束在 M0 就位：runs.signals 必存、spider_versions.rules 配置入库、spiders 执行态/健康态分离。"""
from __future__ import annotations
import uuid
from datetime import datetime

from sqlalchemy import (
    String, Integer, Boolean, Float, ForeignKey, DateTime, func, text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.db import Base
from shared import enums


def _uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


class Project(Base):
    __tablename__ = "projects"
    id: Mapped[uuid.UUID] = _uuid_pk()
    name: Mapped[str] = mapped_column(String(128))
    env: Mapped[str] = mapped_column(String(16), default=enums.Env.dev.value)
    domain: Mapped[str] = mapped_column(String(32), default=enums.Domain.bid.value)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class User(Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = _uuid_pk()
    name: Mapped[str] = mapped_column(String(64))
    email: Mapped[str] = mapped_column(String(128), unique=True)
    role: Mapped[str] = mapped_column(String(32), default="maintainer")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Spider(Base):
    __tablename__ = "spiders"
    id: Mapped[uuid.UUID] = _uuid_pk()
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(128), index=True)
    owner_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    # 执行态 与 健康态 分离（成功率高 ≠ 健康）
    status: Mapped[str] = mapped_column(String(16), default=enums.SpiderExecStatus.paused.value)
    health_status: Mapped[str] = mapped_column(String(20), default=enums.HealthStatus.unknown.value)
    # 业务价值：手填 priority + 自动 contribution_pct + 派生 is_core
    priority: Mapped[str] = mapped_column(String(4), default=enums.Priority.p2.value)
    contribution_pct: Mapped[float] = mapped_column(Float, default=0.0)
    is_core: Mapped[bool] = mapped_column(Boolean, default=False)
    current_version_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    tags: Mapped[list] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    project: Mapped[Project] = relationship()


class SpiderVersion(Base):
    __tablename__ = "spider_versions"
    id: Mapped[uuid.UUID] = _uuid_pk()
    spider_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("spiders.id", ondelete="CASCADE"), index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    # 配置即版本：rules/incremental/hooks 全部入库 JSONB，禁止复制文件当版本
    rules: Mapped[dict] = mapped_column(JSONB, default=dict)
    incremental: Mapped[dict] = mapped_column(JSONB, default=dict)
    hooks: Mapped[list] = mapped_column(JSONB, default=list)
    is_live: Mapped[bool] = mapped_column(Boolean, default=False)
    author_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    change_msg: Mapped[str] = mapped_column(String(512), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Run(Base):
    __tablename__ = "runs"
    id: Mapped[uuid.UUID] = _uuid_pk()
    spider_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("spiders.id", ondelete="CASCADE"), index=True)
    version_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    exec_status: Mapped[str] = mapped_column(String(16), default=enums.RunExecStatus.queued.value, index=True)
    data_outcome: Mapped[str] = mapped_column(String(8), default=enums.DataOutcome.na.value)
    trigger: Mapped[str] = mapped_column(String(16), default=enums.RunTrigger.manual.value)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    stats: Mapped[dict] = mapped_column(JSONB, default=dict)
    # 硬约束：四层信号必存（缺层=null=unknown），作健康判定的唯一真相源
    signals: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Schedule(Base):
    __tablename__ = "schedules"
    id: Mapped[uuid.UUID] = _uuid_pk()
    spider_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("spiders.id", ondelete="CASCADE"), index=True)
    cron: Mapped[str] = mapped_column(String(64))
    queue: Mapped[str] = mapped_column(String(32), default="default")
    priority: Mapped[int] = mapped_column(Integer, default=0)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    jitter_sec: Mapped[int] = mapped_column(Integer, default=0)  # 下发抖动防惊群
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CrawledRecord(Base):
    """业务落库（M3）：抓取产出经统一 Sink 幂等 upsert 到此。
    (spider_id, dedup_key) 唯一 = 已采去重闸门；新插入条数 = 真实 dedup_new。
    MVP 默认 PG（业务数据与元数据同库不同表），可插拔 mysql/kafka（sink.target）。"""
    __tablename__ = "crawled_records"
    id: Mapped[uuid.UUID] = _uuid_pk()
    spider_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("spiders.id", ondelete="CASCADE"), index=True)
    dedup_key: Mapped[str] = mapped_column(String(256), index=True)
    data: Mapped[dict] = mapped_column(JSONB, default=dict)
    run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (UniqueConstraint("spider_id", "dedup_key", name="uq_crawled_spider_key"),)


class DedupRegistry(Base):
    __tablename__ = "dedup_registry"
    id: Mapped[uuid.UUID] = _uuid_pk()
    scope: Mapped[str] = mapped_column(String(8), index=True)  # inque / crawled
    spider_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("spiders.id", ondelete="CASCADE"), index=True)
    key: Mapped[str] = mapped_column(String(256), index=True)
    expire_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
