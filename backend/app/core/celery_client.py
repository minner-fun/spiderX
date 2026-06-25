"""后端用的 Celery 生产端：仅向 broker 投递任务（不执行）。"""
from __future__ import annotations
from celery import Celery
from backend.app.core.config import settings

celery_producer = Celery("spiderx-producer", broker=settings.CELERY_BROKER_URL)
