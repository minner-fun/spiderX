"""上报契约（M0 骨架）：任何爬虫（配置/代码驱动）都须回报 records + 四层 signals，
缺层=null=unknown。代码驱动爬虫通过此 SDK 上报，否则健康判定标 unknown。真实实现在 M2/M3。"""
from __future__ import annotations
from shared.enums import SIGNAL_KEYS


def empty_signals() -> dict:
    return {k: None for k in SIGNAL_KEYS}
