"""本地 fixture：仿真招投标 / IC 列表页 HTML，供 M2 试运行确定性验证（离线可跑）。
真实站点抓取走同一引擎（fetch-page / dry-run 填真实 URL 即可）。"""
from __future__ import annotations

_PAGE_CSS = """
body{font-family:-apple-system,Segoe UI,sans-serif;background:#f5f6f8;color:#1a2230;margin:0;padding:18px}
h1{font-size:18px;margin:0 0 14px}
.notice-list{display:flex;flex-direction:column;gap:10px}
.notice-item{background:#fff;border:1px solid #e3e7ee;border-radius:8px;padding:12px 14px}
.notice-item .notice-title{font-size:14px;color:#1456c4;text-decoration:none;font-weight:600}
.notice-item .meta{margin-top:6px;font-size:12px;color:#6b7585;display:flex;gap:16px}
.pub-date{}.region{}.budget{color:#c4621a}
.pager{margin-top:16px;font-size:12px;color:#6b7585}
"""

_BID = [
    ("中央国家机关2026年办公设备协议供货公开招标公告", "/detail/bid/10241", "2026-06-24", "北京市", "1200.5万元"),
    ("广东省政务云平台扩容项目招标公告", "/detail/bid/10240", "2026-06-24", "广东省", "3680万元"),
    ("深圳市轨道交通信号系统采购项目", "/detail/bid/10238", "2026-06-23", "广东省深圳市", "8900万元"),
    ("江苏省人民医院医疗设备采购公告", "/detail/bid/10235", "2026-06-23", "江苏省", "560.8万元"),
    ("北京市公共资源交易中心智慧化升级", "/detail/bid/10233", "2026-06-22", "北京市", "240万元"),
    ("浙江省高速公路监控系统集成采购", "/detail/bid/10230", "2026-06-22", "浙江省", "1530万元"),
    ("四川省水利厅防汛物资储备采购", "/detail/bid/10228", "2026-06-21", "四川省", "78.3万元"),
    ("上海市某区中小学校园网络改造", "/detail/bid/10225", "2026-06-21", "上海市", "320万元"),
    ("湖北省疾控中心实验室仪器采购", "/detail/bid/10222", "2026-06-20", "湖北省", "990万元"),
    ("山东省港口集团起重设备采购公告", "/detail/bid/10220", "2026-06-20", "山东省", "4200万元"),
    ("福建省气象局雷达系统维保服务", "/detail/bid/10218", "2026-06-19", "福建省", "145万元"),
    ("陕西省图书馆数字资源采购项目", "/detail/bid/10215", "2026-06-19", "陕西省", "86万元"),
]

_IC = [
    ("STM32F407VGT6 ARM Cortex-M4 MCU", "/p/ic/stm32f407", "现货 12,800", "ST", "¥38.50"),
    ("TPS54560DDAR 降压转换器 DC-DC", "/p/ic/tps54560", "现货 45,200", "TI", "¥6.20"),
    ("ESP32-WROOM-32E WiFi 模组", "/p/ic/esp32wroom", "现货 8,600", "Espressif", "¥18.90"),
    ("ADUM1201ARZ 数字隔离器", "/p/ic/adum1201", "现货 3,200", "ADI", "¥9.80"),
    ("LM2596S-ADJ 开关稳压器", "/p/ic/lm2596s", "现货 67,000", "TI", "¥2.45"),
    ("CH340G USB 转串口芯片", "/p/ic/ch340g", "现货 120,000", "WCH", "¥1.30"),
    ("W25Q128JVSIQ 128Mbit NOR Flash", "/p/ic/w25q128", "现货 22,400", "Winbond", "¥4.10"),
    ("MAX3232ESE+ RS-232 收发器", "/p/ic/max3232", "现货 9,900", "Maxim", "¥5.60"),
]


def _bid_page() -> str:
    items = "\n".join(
        f'''<div class="notice-item">
  <a class="notice-title" href="{href}">{title}</a>
  <div class="meta"><span class="pub-date">{date}</span>'''
        f'''<span class="region">{region}</span><span class="budget">预算 {budget}</span></div>
</div>'''
        for title, href, date, region, budget in _BID
    )
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<title>招标公告列表 · SpiderX Fixture</title><style>{_PAGE_CSS}</style></head>
<body><h1>全国招标公告（仿真 fixture）</h1>
<div class="notice-list">
{items}
</div>
<div class="pager">第 1 / 128 页 · 共 1,532 条</div>
</body></html>'''


def _ic_page() -> str:
    items = "\n".join(
        f'''<div class="notice-item">
  <a class="notice-title" href="{href}">{name}</a>
  <div class="meta"><span class="stock">{stock}</span>'''
        f'''<span class="brand">{brand}</span><span class="budget">{price}</span></div>
</div>'''
        for name, href, stock, brand, price in _IC
    )
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<title>元器件现货列表 · SpiderX Fixture</title><style>{_PAGE_CSS}</style></head>
<body><h1>IC 元器件现货（仿真 fixture）</h1>
<div class="notice-list">
{items}
</div>
<div class="pager">第 1 / 64 页 · 共 508 条</div>
</body></html>'''


FIXTURES = {
    "bid-list": _bid_page,
    "ic-list": _ic_page,
}


def render(name: str) -> str | None:
    fn = FIXTURES.get(name)
    return fn() if fn else None


# 与 fixture 结构匹配的默认规则模板（编辑器新建/重置时用）
DEFAULT_RULES_BID = {
    "entries": [{"list_url_template": "/api/fixtures/bid-list?page={page}"}],
    "processors": [{
        "url_reg": ".*bid-list.*", "type": "list", "row_selector": "div.notice-item",
        "fields": [
            {"name": "title", "selector": "a.notice-title", "type": "text"},
            {"name": "link", "selector": "a.notice-title", "attr": "href", "type": "text"},
            {"name": "pub_time", "selector": "span.pub-date", "type": "date"},
            {"name": "region", "selector": "span.region", "type": "area"},
            {"name": "budget", "selector": "span.budget", "type": "money"},
        ],
        "pagination": {"param": "page", "stop": "命中水位 | 连续N条已采"},
    }],
    "incremental": {"field": "pub_time", "watermark_key": "bid:wm", "window": "3d"},
    "sink": {"target": "pg", "table": "bid_notices", "dedup_key": "title+pub_time"},
}
