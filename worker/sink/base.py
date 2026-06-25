"""Sink 抽象（M0 骨架）：抓取产出 records → 统一落库，幂等 upsert。
可插拔多目标（pg/mysql/kafka），M0 默认 PG。真实实现在 M3。"""
from __future__ import annotations
from abc import ABC, abstractmethod


class Sink(ABC):
    @abstractmethod
    def write(self, records: list[dict], *, table: str, dedup_key: str) -> int:
        """批量幂等 upsert，返回新增条数。"""
        ...


class PgSink(Sink):
    def write(self, records: list[dict], *, table: str, dedup_key: str) -> int:
        # M0 占位：M3 实现 ON CONFLICT upsert + 去重统计
        raise NotImplementedError("PgSink.write 在 M3 实现")
