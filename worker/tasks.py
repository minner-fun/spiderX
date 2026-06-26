"""worker 任务。
- ping_run：M0 自检骨架（保留）。
- run_spider（M3）：真实执行 = 引擎抓首页 → 解析 → 统一 Sink 幂等 upsert →
  产出真实四层信号(含 L4 dedup_new) → Run 状态机 → 更新 health_status → 推 triage。
- dispatch_due / reconcile（M3）：Beat 周期任务（调度下发 + 对账）。"""
from __future__ import annotations
import asyncio
import os
import uuid
from datetime import datetime, timezone, timedelta

from worker.celery_app import celery_app
from worker.engine import core as engine
from worker.sink import pg as pg_sink
from shared.db import sync_session_maker
from shared.models import Run, Spider, SpiderVersion, Schedule
from shared.redis_bus import publish_sync
from shared.health import verdict
from shared.enums import (
    RunExecStatus, DataOutcome, RunTrigger, HealthStatus, CH_TRIAGE, SIGNAL_KEYS,
)

UTC = timezone.utc
# worker 与 backend 是不同容器：相对 fixture 路径要走服务名 backend
INTERNAL_API_BASE = os.getenv("INTERNAL_API_BASE", "http://backend:8000")


def _resolve(url: str) -> str:
    return f"{INTERNAL_API_BASE}{url}" if url.startswith("/") else url


def _entry_url(rules: dict) -> str | None:
    entries = rules.get("entries") or []
    if not entries:
        return None
    tpl = entries[0].get("list_url_template", "")
    for ph, val in (("{page}", "1"), ("{watermark}", ""), ("{begin}", "")):
        tpl = tpl.replace(ph, val)
    return tpl or None


@celery_app.task(name="worker.ping_run")
def ping_run(spider_id: str) -> str:
    """M0 自检：写一条占位 Run（不真实抓取）。保留作链路自检。"""
    now = datetime.now(UTC)
    signals = {k: None for k in SIGNAL_KEYS}
    signals["http_status"] = 200
    with sync_session_maker() as s:
        spider = s.get(Spider, uuid.UUID(spider_id))
        run = Run(spider_id=uuid.UUID(spider_id), exec_status=RunExecStatus.success.value,
                  data_outcome=DataOutcome.na.value, trigger=RunTrigger.manual.value,
                  started_at=now, finished_at=datetime.now(UTC),
                  stats={"note": "ping_run 自检"}, signals=signals)
        s.add(run); s.commit(); s.refresh(run)
        run_id, spider_name = str(run.id), (spider.name if spider else "?")
    publish_sync(CH_TRIAGE, {"type": "run_done", "spider_id": spider_id,
                             "spider_name": spider_name, "run_id": run_id,
                             "verdict": HealthStatus.unknown.value, "ts": now.isoformat()})
    return run_id


@celery_app.task(name="worker.run_spider", bind=True, max_retries=2, default_retry_delay=5)
def run_spider(self, spider_id: str, trigger: str = "manual") -> str:
    """真实执行一次：fetch → parse → sink → 四层信号 → Run + health + triage。"""
    now = datetime.now(UTC)
    sid = uuid.UUID(spider_id)

    with sync_session_maker() as s:
        spider = s.get(Spider, sid)
        if not spider:
            return "spider not found"
        version = (
            s.get(SpiderVersion, spider.current_version_id)
            if spider.current_version_id else None
        )
        rules = (version.rules if version else {}) or {}
        version_id = version.id if version else None

        # Run：queued → running（late-ack：执行成功才 ack，此处先落 running 行作真相源）
        run = Run(spider_id=sid, version_id=version_id,
                  exec_status=RunExecStatus.running.value, data_outcome=DataOutcome.na.value,
                  trigger=trigger, started_at=now, signals={k: None for k in SIGNAL_KEYS})
        s.add(run); s.commit(); s.refresh(run)
        run_id = run.id

        url = _entry_url(rules)
        signals = {k: None for k in SIGNAL_KEYS}
        new_count = dup_count = 0
        exec_status = RunExecStatus.failed.value
        outcome = DataOutcome.na.value
        note = ""

        if not url:
            note = "rules 无 entries.list_url_template"
        else:
            res = asyncio.run(engine.dry_run(_resolve(url), rules, sample=100000))
            signals["http_status"] = res["http_status"]
            signals["list_rows"] = res["list_rows"]
            signals["field_fill_rate"] = res["field_fill_rate"]
            if res["http_status"] == 200 and res.get("error") is None:
                # 统一 Sink：幂等 upsert → 真实 dedup_new / duplicate（已采去重闸门）
                dedup_spec = (rules.get("sink") or {}).get("dedup_key", "")
                new_count, dup_count = pg_sink.write(
                    s, res["records"], spider_id=sid, run_id=run_id, dedup_key_spec=dedup_spec)
                signals["dedup_new"] = new_count
                signals["duplicate"] = dup_count
                signals["watermark_hit"] = bool(dup_count) or None
                exec_status = RunExecStatus.success.value
                outcome = DataOutcome.new.value if new_count > 0 else DataOutcome.dry.value
                note = f"抓 {res['list_rows']} 行，新增 {new_count}，重复 {dup_count}"
            else:
                note = res.get("error") or f"HTTP {res['http_status']}"

        # 收尾 Run + 健康判定（真实信号驱动 health_status）
        run.exec_status = exec_status
        run.data_outcome = outcome
        run.signals = signals
        run.finished_at = datetime.now(UTC)
        run.stats = {"note": note}
        new_health = verdict(signals)
        spider.health_status = new_health
        if trigger == RunTrigger.cron.value:
            sched = s.scalar(
                Schedule.__table__.select().where(Schedule.spider_id == sid).limit(1)
            )
            # 更新 last_run_at（容错：可能无 schedule）
            if sched is not None:
                s.execute(Schedule.__table__.update()
                          .where(Schedule.spider_id == sid)
                          .values(last_run_at=now))
        s.commit()
        spider_name = spider.name

    publish_sync(CH_TRIAGE, {
        "type": "run_done", "spider_id": spider_id, "spider_name": spider_name,
        "run_id": str(run_id), "verdict": new_health,
        "new": new_count, "rows": signals.get("list_rows"),
        "ts": datetime.now(UTC).isoformat(),
    })
    return str(run_id)
