"""配置驱动 async 通用爬虫引擎（M2）。
输入 = SpiderVersion.rules（entries/processors/fields）+ 一个 URL；
输出 = 抽取记录 + 真实四层信号。被 backend 试运行(dry-run) 与 worker 真实执行(M3) 共用。

设计对齐纲要 §3：URL 正则 → processor 路由（借鉴 Sardinia），字段 selector + transform。
缺层 = null = unknown（四层信号契约）。"""
from __future__ import annotations
import re
from typing import Any

import httpx
from parsel import Selector

from shared.enums import SIGNAL_KEYS

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36 SpiderX/0.2"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9",
}


# ——————————————————————————— 抓取 ———————————————————————————

async def fetch(url: str, *, timeout: float = 15.0, headers: dict | None = None) -> tuple[int, str]:
    """抓单页，返回 (http_status, html)。网络异常以 status=0 表达。"""
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=timeout) as client:
            r = await client.get(url, headers=headers or DEFAULT_HEADERS)
            return r.status_code, r.text
    except httpx.HTTPError:
        return 0, ""


# ——————————————————————————— transform ———————————————————————————

_DATE_RE = re.compile(r"(\d{4})[-/年.](\d{1,2})[-/月.](\d{1,2})")
_NUM_RE = re.compile(r"-?\d+(?:\.\d+)?")


def apply_transform(value: str | None, conv: str | None) -> Any:
    """字段转换：text/trim(默认) · int · money(万元→元) · date(归一 YYYY-MM-DD) · area。"""
    if value is None:
        return None
    v = value.strip()
    if not conv or conv in ("text", "trim", "str"):
        return v or None
    if conv == "int":
        m = _NUM_RE.search(v.replace(",", ""))
        return int(float(m.group())) if m else None
    if conv == "money":
        m = _NUM_RE.search(v.replace(",", ""))
        if not m:
            return None
        num = float(m.group())
        if "万" in v:
            num *= 10000
        return round(num, 2)
    if conv == "date":
        m = _DATE_RE.search(v)
        return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}" if m else None
    if conv == "area":
        return v or None
    return v or None


# ——————————————————————————— 解析 ———————————————————————————

def _extract_field(row: Selector, field: dict) -> Any:
    selector = field.get("selector") or ""
    if not selector:
        return None
    node = row.css(selector)
    if not node:
        return None
    attr = field.get("attr")
    if attr:
        raw = node.attrib.get(attr)
    else:
        raw = "".join(node.css("::text").getall())
    return apply_transform(raw, field.get("transform") or field.get("type"))


def parse_list(html: str, processor: dict) -> tuple[list[dict], int, float | None]:
    """列表页解析：返回 (records, list_rows, field_fill_rate)。"""
    sel = Selector(text=html)
    row_selector = processor.get("row_selector") or ""
    rows = sel.css(row_selector) if row_selector else []
    fields: list[dict] = processor.get("fields", [])

    records: list[dict] = []
    total_cells = 0
    filled_cells = 0
    for row in rows:
        rec: dict[str, Any] = {}
        for f in fields:
            val = _extract_field(row, f)
            rec[f["name"]] = val
            total_cells += 1
            if val not in (None, "", []):
                filled_cells += 1
        records.append(rec)

    fill_rate = round(filled_cells / total_cells, 4) if total_cells else None
    return records, len(rows), fill_rate


def route(url: str, processors: list[dict]) -> dict | None:
    """URL 正则 → processor。命中 url_reg 优先；否则取第一个 list 型；再否则第一个。"""
    for p in processors:
        reg = p.get("url_reg")
        if reg and re.search(reg, url):
            return p
    for p in processors:
        if p.get("type") == "list":
            return p
    return processors[0] if processors else None


# ——————————————————————————— 试运行 ———————————————————————————

def empty_signals() -> dict:
    return {k: None for k in SIGNAL_KEYS}


async def dry_run(url: str, rules: dict, *, sample: int = 50) -> dict:
    """配置 + URL → 抓首页 → 抽字段 + 真实四层信号（L1 HTTP / L2 list_rows / L3 fill_rate）。
    试运行不接去重闸门，故 L4 dedup_new=null（真实去重在 M3 执行落库时产出）。"""
    status, html = await fetch(url)
    signals = empty_signals()
    signals["http_status"] = status

    out: dict[str, Any] = {
        "http_status": status, "list_rows": None, "field_fill_rate": None,
        "record_count": 0, "records": [], "signals": signals, "error": None,
    }
    if status != 200:
        out["error"] = "fetch 失败" if status == 0 else f"HTTP {status}"
        return out

    processor = route(url, rules.get("processors", []))
    if not processor:
        out["error"] = "rules 未定义 processors"
        return out

    try:
        records, n, fill = parse_list(html, processor)
    except Exception as e:  # selector 语法错误等
        out["error"] = f"解析错误: {e}"
        return out

    signals["list_rows"] = n
    signals["field_fill_rate"] = fill
    out.update(list_rows=n, field_fill_rate=fill, record_count=len(records), records=records[:sample])
    return out
