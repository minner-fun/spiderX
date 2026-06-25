"""Celery 应用：broker 用 Redis，含 Beat（M0 暂无定时，M3 接入调度）。"""
from __future__ import annotations
import os
from celery import Celery

celery_app = Celery(
    "spiderx",
    broker=os.getenv("CELERY_BROKER_URL", "redis://redis:6379/1"),
    include=["worker.tasks"],
)
celery_app.conf.update(
    task_acks_late=True,                 # 执行成功才 ack（防 IC 项目那种 early-ack 丢数据）
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,        # 有界预取
    timezone="Asia/Shanghai",
    # M0 用 Celery 默认队列，保证生产端/消费端一致；M3 再引入 default/high/retry/low 命名队列
)
