"""worker 任务。M0 只有 ping_run：写一条 Run（带四层信号占位）+ 实时推送，
验证「调度→worker→入库→pub-sub」全链路。真实抓取引擎在 M2/M3 接入。"""
from __future__ import annotations
import uuid
from datetime import datetime, timezone

from worker.celery_app import celery_app
from shared.db import sync_session_maker
from shared.models import Run, Spider
from shared.redis_bus import publish_sync
from shared.enums import (
    RunExecStatus, DataOutcome, RunTrigger, HealthStatus, CH_TRIAGE, SIGNAL_KEYS,
)


@celery_app.task(name="worker.ping_run")
def ping_run(spider_id: str) -> str:
    now = datetime.now(timezone.utc)
    # M0 占位四层信号（M2/M3 由真实引擎填充）
    signals = {k: None for k in SIGNAL_KEYS}
    signals["http_status"] = 200

    with sync_session_maker() as s:
        spider = s.get(Spider, uuid.UUID(spider_id))
        run = Run(
            spider_id=uuid.UUID(spider_id),
            exec_status=RunExecStatus.success.value,
            data_outcome=DataOutcome.na.value,
            trigger=RunTrigger.manual.value,
            started_at=now,
            finished_at=datetime.now(timezone.utc),
            stats={"note": "M0 ping_run，无真实抓取"},
            signals=signals,
        )
        s.add(run)
        s.commit()
        s.refresh(run)
        run_id = str(run.id)
        spider_name = spider.name if spider else "?"

    publish_sync(CH_TRIAGE, {
        "type": "run_done",
        "spider_id": spider_id,
        "spider_name": spider_name,
        "run_id": run_id,
        "verdict": HealthStatus.unknown.value,
        "ts": now.isoformat(),
    })
    return run_id
