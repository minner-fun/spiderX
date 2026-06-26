"""M3 demo seed（幂等）：真实域占位数据，撑「成功率≠健康」叙事 + 版本/运行 + 调度。
关键：健康现在是真信号驱动 —— 每只爬虫的 rules 设计成跑起来就产出其「应有」的健康态：
  ok → 🟢 / broken(错 selector)→🔴 / blocked(403)→🔴 / dry(预置已采)→🟡 / code(无 entries)→⚪。
故 beat/手动跑都不会破坏叙事，反而印证。占位用真实域：招投标 / IC 元器件。"""
from __future__ import annotations
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models import (
    Project, User, Spider, SpiderVersion, Run, Schedule, CrawledRecord,
)
from shared.enums import (
    Env, Domain, SpiderExecStatus, HealthStatus, Priority,
    RunExecStatus, DataOutcome, RunTrigger, SIGNAL_KEYS,
)
from backend.app import fixtures
from worker.sink.pg import dedup_key

UTC = timezone.utc


def _sig(http=200, rows=None, fill=None, new=None, dup=None, miss=None, wm=None) -> dict:
    s = {k: None for k in SIGNAL_KEYS}
    s.update(http_status=http, list_rows=rows, field_fill_rate=fill,
             dedup_new=new, duplicate=dup, missing_rate=miss, watermark_hit=wm)
    return s


# —— 各域字段 + 落库去重键（与 fixture 结构匹配）——
FIELDS_BID = [
    {"name": "title", "selector": "a.notice-title", "type": "text"},
    {"name": "link", "selector": "a.notice-title", "attr": "href", "type": "text"},
    {"name": "pub_time", "selector": "span.pub-date", "type": "date"},
    {"name": "region", "selector": "span.region", "type": "area"},
    {"name": "budget", "selector": "span.budget", "type": "money"},
]
FIELDS_IC = [
    {"name": "title", "selector": "a.notice-title", "type": "text"},
    {"name": "link", "selector": "a.notice-title", "attr": "href", "type": "text"},
    {"name": "stock", "selector": "span.stock", "type": "text"},
    {"name": "brand", "selector": "span.brand", "type": "text"},
    {"name": "price", "selector": "span.budget", "type": "money"},
]
DEDUP_KEY = {Domain.bid: "title+pub_time", Domain.ic: "title"}


def build_rules(kind: str, domain: Domain, v: int) -> dict:
    """按 kind 生成会真实产出对应健康态的规则。"""
    fixture = "bid-list" if domain == Domain.bid else "ic-list"
    fields = FIELDS_BID if domain == Domain.bid else FIELDS_IC
    # blocked：入口指向 403 站；broken：行选择器故意写错（改版后失效）
    entry = "/api/fixtures/blocked" if kind == "blocked" else f"/api/fixtures/{fixture}?page={{page}}&begin={{watermark}}"
    row_selector = "div.legacy-item" if kind == "broken" else "div.notice-item"
    rules = {
        "entries": [] if kind == "code" else [{"list_url_template": entry}],
        "processors": [{
            "url_reg": ".*(list|blocked).*", "type": "list", "row_selector": row_selector,
            "fields": fields,
        }],
        "incremental": {"field": "pub_time", "watermark_key": f"{domain.value}:wm", "window": "3d"},
        "sink": {"target": "pg", "table": f"{domain.value}_records", "dedup_key": DEDUP_KEY[domain]},
        "_v": v,
    }
    return rules


# 剧本：name, domain, kind, exec, priority, contrib%, is_core, cron, sr, versions, owner, note
# kind 决定真实健康态：ok🟢 / broken🔴 / blocked🔴 / dry🟡 / code⚪
SPIDERS = [
    dict(name="中国政府采购网-中央", domain=Domain.bid, kind="broken",
         exec=SpiderExecStatus.running, prio=Priority.p0, contrib=18.0, core=True,
         cron="0 * * * *", sr=0.991, versions=3, owner="李航",
         note="HTTP 200 但 list selector 命中 0 行 → 改版结构故障（编辑器里修 selector）"),
    dict(name="广东省政府采购网", domain=Domain.bid, kind="ok",
         exec=SpiderExecStatus.running, prio=Priority.p0, contrib=12.4, core=True,
         cron="0 * * * *", sr=0.985, versions=2, owner="李航"),
    dict(name="深圳交易集团", domain=Domain.bid, kind="dry",
         exec=SpiderExecStatus.running, prio=Priority.p1, contrib=4.1, core=False,
         cron="*/30 * * * *", sr=0.978, versions=4, owner="王敏",
         note="列表/字段正常但去重后新增=0（已采满）→ 真没数据，待确认"),
    dict(name="北京市公共资源交易", domain=Domain.bid, kind="ok",
         exec=SpiderExecStatus.running, prio=Priority.p1, contrib=3.2, core=False,
         cron="0 */2 * * *", sr=0.96, versions=1, owner="王敏"),
    dict(name="江苏省采购中心", domain=Domain.bid, kind="ok",
         exec=SpiderExecStatus.running, prio=Priority.p2, contrib=2.0, core=False,
         cron="0 */3 * * *", sr=0.94, versions=2, owner="赵强"),
    dict(name="IC-Digikey 现货", domain=Domain.ic, kind="blocked",
         exec=SpiderExecStatus.failed, prio=Priority.p1, contrib=6.8, core=True,
         cron="*/15 * * * *", sr=0.62, versions=5, owner="赵强",
         note="HTTP 403 封禁 → 代理/凭据层故障"),
    dict(name="IC-Mouser 库存", domain=Domain.ic, kind="dry",
         exec=SpiderExecStatus.running, prio=Priority.p2, contrib=1.4, core=False,
         cron="0 */1 * * *", sr=0.97, versions=2, owner="王敏"),
    dict(name="裁判文书网（代码驱动）", domain=Domain.bid, kind="code",
         exec=SpiderExecStatus.paused, prio=Priority.p1, contrib=0.0, core=False,
         cron=None, sr=None, versions=1, owner="赵强",
         note="代码驱动未按契约回报四层信号 → 健康未知"),
    dict(name="安徽省招投标", domain=Domain.bid, kind="ok",
         exec=SpiderExecStatus.disabled, prio=Priority.p2, contrib=0.5, core=False,
         cron="0 8 * * *", sr=0.99, versions=1, owner="李航"),
]

# kind → (健康态, 最近一次 Run 的信号原型)
_KIND_HEALTH = {
    "ok": (HealthStatus.healthy, _sig(rows=12, fill=1.0, new=8, dup=4, wm=True)),
    "broken": (HealthStatus.structural_fail, _sig(rows=0, fill=None, new=None)),
    "blocked": (HealthStatus.structural_fail, _sig(http=403, rows=None, new=None)),
    "dry": (HealthStatus.data_dry, _sig(rows=12, fill=1.0, new=0, dup=12, wm=True)),
    "code": (HealthStatus.unknown, None),
}


async def seed_demo(s: AsyncSession) -> None:
    count = await s.scalar(select(sa_func.count()).select_from(Project))
    if count:
        return

    now = datetime.now(UTC)
    projects: dict[Domain, Project] = {
        Domain.bid: Project(name="demo-招投标", env=Env.prod.value, domain=Domain.bid.value),
        Domain.ic: Project(name="demo-IC元器件", env=Env.staging.value, domain=Domain.ic.value),
    }
    for p in projects.values():
        s.add(p)
    await s.flush()

    names = ["李航", "王敏", "赵强"]
    users: dict[str, User] = {}
    for i, n in enumerate(names):
        users[n] = User(name=n, email=f"{['lihang','wangmin','zhaoqiang'][i]}@spiderx.team", role="maintainer")
        s.add(users[n])
    s.add(User(name="ops", email="ops@spiderx.local", role="owner"))
    await s.flush()

    for sc in SPIDERS:
        domain = sc["domain"]
        health, latest_sig = _KIND_HEALTH[sc["kind"]]
        sp = Spider(
            project_id=projects[domain].id, name=sc["name"], owner_id=users[sc["owner"]].id,
            status=sc["exec"].value, health_status=health.value,
            priority=sc["prio"].value, contribution_pct=sc["contrib"], is_core=sc["core"],
            tags=[domain.name, "核心站" if sc["core"] else "长尾"],
        )
        s.add(sp)
        await s.flush()

        live_version_no = sc["versions"]
        for v in range(1, sc["versions"] + 1):
            ver = SpiderVersion(
                spider_id=sp.id, version=v, rules=build_rules(sc["kind"], domain, v),
                incremental={"field": "pub_time", "watermark_key": f"{sp.name}:wm", "window": "3d"},
                hooks=[] if domain != Domain.ic else ["sign"],
                is_live=(v == live_version_no), author_id=users[sc["owner"]].id,
                change_msg=(f"v{v} 初始化规则" if v == 1 else f"v{v} 调整 selector / 字段映射"),
                created_at=now - timedelta(days=(sc["versions"] - v) * 5 + 1),
            )
            s.add(ver)
            await s.flush()
            if v == live_version_no:
                sp.current_version_id = ver.id

        # 调度：last_run_at=now，避免 beat 启动时把所有站立刻重跑（按 cron 周期才再触发）
        if sc["cron"]:
            s.add(Schedule(spider_id=sp.id, cron=sc["cron"], queue="default", jitter_sec=30,
                           enabled=(sc["exec"] != SpiderExecStatus.disabled), last_run_at=now))

        # dry 站：预置「已采」记录到 crawled_records，使真实首跑 dedup_new=0 → 真·data_dry
        if sc["kind"] == "dry":
            rows = fixtures._BID if domain == Domain.bid else fixtures._IC
            spec = DEDUP_KEY[domain]
            for row in rows:
                rec = ({"title": row[0], "pub_time": row[2]} if domain == Domain.bid
                       else {"title": row[0]})
                s.add(CrawledRecord(spider_id=sp.id, dedup_key=dedup_key(rec, spec),
                                    data=rec, first_seen_at=now - timedelta(days=2)))

        # 运行历史：近 10 次（撑趋势柱图）。最近一次=剧本信号；历史为基线（曾正常）。
        sr = sc["sr"]
        for k in range(10):
            ts = now - timedelta(hours=k * 6 + 1)
            if k == 0 and latest_sig is not None:
                signals = latest_sig
            elif latest_sig is None:
                signals = {kk: None for kk in SIGNAL_KEYS}
            else:
                base_new = 18 + (k % 5) * 6
                signals = _sig(rows=12, fill=1.0, new=base_new, dup=4, wm=True)
            failed = sr is not None and sr < 0.9 and (k in (2, 5))
            exec_status = RunExecStatus.failed if failed else RunExecStatus.success
            outcome = (DataOutcome.new if (signals.get("dedup_new") or 0) > 0
                       else DataOutcome.dry if signals.get("list_rows") is not None
                       else DataOutcome.na)
            s.add(Run(
                spider_id=sp.id, version_id=sp.current_version_id,
                exec_status=exec_status.value, data_outcome=outcome.value,
                trigger=RunTrigger.cron.value if sc["cron"] else RunTrigger.manual.value,
                started_at=ts, finished_at=ts + timedelta(minutes=2),
                stats={"note": sc.get("note", "")}, signals=signals, created_at=ts,
            ))

    await s.commit()
