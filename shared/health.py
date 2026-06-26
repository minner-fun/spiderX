"""四层信号 → 健康判定（与前端 utils/health.ts 同逻辑，纲要 §5）。
①②③任一异常=🔴；①②③正常且④=0=🟡；④>0=🟢；关键层 null=⚪。"""
from __future__ import annotations

from shared.enums import HealthStatus


def verdict(signals: dict) -> str:
    http = signals.get("http_status")
    rows = signals.get("list_rows")
    fill = signals.get("field_fill_rate")
    new = signals.get("dedup_new")

    if http is None:
        return HealthStatus.unknown.value
    if http != 200:
        return HealthStatus.structural_fail.value      # L1 异常
    if rows is None:
        return HealthStatus.unknown.value
    if rows == 0:
        return HealthStatus.structural_fail.value      # L2 命中 0 行
    if fill is not None and fill < 0.8:
        return HealthStatus.structural_fail.value      # L3 抽取率低
    if new is None:
        return HealthStatus.unknown.value              # L4 未上报
    if new > 0:
        return HealthStatus.healthy.value              # 🟢 出数据
    return HealthStatus.data_dry.value                 # 🟡 前三正常但无新增
