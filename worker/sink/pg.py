"""PgSink（M3）：抓取产出 records → 幂等 upsert 到 crawled_records。
已采去重闸门 = (spider_id, dedup_key) 唯一约束；ON CONFLICT DO NOTHING，
实插入条数 = 真实 dedup_new，重复数 = 总数 - 新增。"""
from __future__ import annotations
import hashlib
import uuid

from sqlalchemy import text
from sqlalchemy.orm import Session

from shared.models import CrawledRecord


def dedup_key(record: dict, key_spec: str) -> str:
    """按 sink.dedup_key（如 "title+pub_time"）拼接字段值 → sha1。"""
    fields = [f.strip() for f in key_spec.split("+") if f.strip()]
    raw = "|".join(str(record.get(f, "")) for f in fields) if fields else str(record)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def write(
    session: Session, records: list[dict], *,
    spider_id: uuid.UUID, run_id: uuid.UUID, dedup_key_spec: str,
) -> tuple[int, int]:
    """批量幂等 upsert，返回 (新增数, 重复数)。"""
    if not records:
        return 0, 0
    keys = [dedup_key(r, dedup_key_spec) for r in records]

    # 已存在的 key（已采去重）
    existing = set(session.scalars(
        text("SELECT dedup_key FROM crawled_records "
             "WHERE spider_id = :sid AND dedup_key = ANY(:keys)").bindparams(
            sid=spider_id, keys=keys)
    ).all())

    new_count = 0
    seen_this_batch: set[str] = set()
    for rec, k in zip(records, keys):
        if k in existing or k in seen_this_batch:
            continue
        seen_this_batch.add(k)
        session.add(CrawledRecord(spider_id=spider_id, dedup_key=k, data=rec, run_id=run_id))
        new_count += 1

    session.flush()
    return new_count, len(records) - new_count
