"""M1 demo seed（幂等）：真实域占位数据，撑起「成功率≠健康」叙事 + 版本/运行。
占位用真实域：招投标 / IC 元器件。重跑只在空库时插入。"""
from __future__ import annotations
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models import Project, User, Spider, SpiderVersion, Run, Schedule
from shared.enums import (
    Env, Domain, SpiderExecStatus, HealthStatus, Priority,
    RunExecStatus, DataOutcome, RunTrigger, SIGNAL_KEYS,
)

UTC = timezone.utc


def _sig(http=200, rows=None, fill=None, new=None, dup=None, miss=None, wm=None) -> dict:
    s = {k: None for k in SIGNAL_KEYS}
    s.update(http_status=http, list_rows=rows, field_fill_rate=fill,
             dedup_new=new, duplicate=dup, missing_rate=miss, watermark_hit=wm)
    return s


# 每个 spider 的剧本：name, domain, health, exec, priority, contrib%, is_core, cron,
# success_rate, 最近 Run 的信号原型, 版本数, owner
SPIDERS = [
    # 🔴 招牌叙事：跑成功率 99% 但 list 命中 0 → 结构故障
    dict(name="中国政府采购网-中央", domain=Domain.bid, health=HealthStatus.structural_fail,
         exec=SpiderExecStatus.running, prio=Priority.p0, contrib=18.0, core=True,
         cron="0 * * * *", sr=0.991,
         sig=_sig(rows=0, fill=None, new=0), versions=3, owner="李航",
         note="HTTP 200 但 list selector 命中 0 行 → 改版结构故障"),
    # 🟢 健康核心站
    dict(name="广东省政府采购网", domain=Domain.bid, health=HealthStatus.healthy,
         exec=SpiderExecStatus.running, prio=Priority.p0, contrib=12.4, core=True,
         cron="0 * * * *", sr=0.985,
         sig=_sig(rows=48, fill=0.97, new=37, dup=11, wm=True), versions=2, owner="李航"),
    # 🟡 数据干涸：前三层正常，去重后新增 0 多日
    dict(name="深圳交易集团", domain=Domain.bid, health=HealthStatus.data_dry,
         exec=SpiderExecStatus.running, prio=Priority.p1, contrib=4.1, core=False,
         cron="*/30 * * * *", sr=0.978,
         sig=_sig(rows=42, fill=0.96, new=0, dup=42, wm=True), versions=4, owner="王敏",
         note="列表/字段正常但去重后新增=0 已 3 天 → 待确认真没数据"),
    # 🟢 健康长尾
    dict(name="北京市公共资源交易", domain=Domain.bid, health=HealthStatus.healthy,
         exec=SpiderExecStatus.running, prio=Priority.p1, contrib=3.2, core=False,
         cron="0 */2 * * *", sr=0.96,
         sig=_sig(rows=31, fill=0.95, new=22, dup=9, wm=True), versions=1, owner="王敏"),
    dict(name="江苏省采购中心", domain=Domain.bid, health=HealthStatus.healthy,
         exec=SpiderExecStatus.running, prio=Priority.p2, contrib=2.0, core=False,
         cron="0 */3 * * *", sr=0.94,
         sig=_sig(rows=27, fill=0.93, new=15, dup=12, wm=True), versions=2, owner="赵强"),
    # 🔴 IC 域：HTTP 403 封禁
    dict(name="IC-Digikey 现货", domain=Domain.ic, health=HealthStatus.structural_fail,
         exec=SpiderExecStatus.failed, prio=Priority.p1, contrib=6.8, core=True,
         cron="*/15 * * * *", sr=0.62,
         sig=_sig(http=403, rows=None, new=None), versions=5, owner="赵强",
         note="HTTP 403 封禁 → 代理/凭据层故障"),
    # 🟡 IC 干涸
    dict(name="IC-Mouser 库存", domain=Domain.ic, health=HealthStatus.data_dry,
         exec=SpiderExecStatus.running, prio=Priority.p2, contrib=1.4, core=False,
         cron="0 */1 * * *", sr=0.97,
         sig=_sig(rows=120, fill=0.99, new=0, dup=120, wm=True), versions=2, owner="王敏"),
    # ⚪ 代码驱动未按契约上报 → unknown
    dict(name="裁判文书网（代码驱动）", domain=Domain.bid, health=HealthStatus.unknown,
         exec=SpiderExecStatus.paused, prio=Priority.p1, contrib=0.0, core=False,
         cron=None, sr=None,
         sig=None, versions=1, owner="赵强",
         note="代码驱动未按契约回报四层信号 → 健康未知"),
    # 🟢 已停用历史站
    dict(name="安徽省招投标", domain=Domain.bid, health=HealthStatus.healthy,
         exec=SpiderExecStatus.disabled, prio=Priority.p2, contrib=0.5, core=False,
         cron="0 8 * * *", sr=0.99,
         sig=_sig(rows=12, fill=0.9, new=0, dup=12, wm=True), versions=1, owner="李航"),
]

# 与本地 fixture 结构匹配（div.notice-item / a.notice-title / span.pub-date…），
# 故 seeded 爬虫的规则在规则编辑器里对 fixture 试运行即可正常产出四层信号。
RULES_BASE = {
    "entries": [{"list_url_template": "/api/fixtures/bid-list?page={page}&begin={watermark}"}],
    "processors": [
        {"url_reg": ".*list.*", "type": "list", "row_selector": "div.notice-item",
         "fields": [
             {"name": "title", "selector": "a.notice-title", "type": "text"},
             {"name": "link", "selector": "a.notice-title", "attr": "href", "type": "text"},
             {"name": "pub_time", "selector": "span.pub-date", "type": "date"},
             {"name": "region", "selector": "span.region", "type": "area"},
             {"name": "budget", "selector": "span.budget", "type": "money"},
         ]},
    ],
    "sink": {"target": "pg", "table": "bid_notices", "dedup_key": "title+pub_time"},
}


async def seed_demo(s: AsyncSession) -> None:
    """空库时插入 demo：1 project + users + 多 spider（含版本/运行/调度）。"""
    count = await s.scalar(select(sa_func.count()).select_from(Project))
    if count:
        return

    now = datetime.now(UTC)
    # 按域分项目（多租户）：招投标 / IC 元器件。spider.domain = 其所属 project.domain。
    projects: dict[Domain, Project] = {
        Domain.bid: Project(name="demo-招投标", env=Env.prod.value, domain=Domain.bid.value),
        Domain.ic: Project(name="demo-IC元器件", env=Env.staging.value, domain=Domain.ic.value),
    }
    for p in projects.values():
        s.add(p)
    await s.flush()

    # 作者
    names = ["李航", "王敏", "赵强"]
    users: dict[str, User] = {}
    for i, n in enumerate(names):
        u = User(name=n, email=f"{['lihang','wangmin','zhaoqiang'][i]}@spiderx.team",
                 role="maintainer")
        s.add(u)
        users[n] = u
    ops = User(name="ops", email="ops@spiderx.local", role="owner")
    s.add(ops)
    await s.flush()

    for sc in SPIDERS:
        sp = Spider(
            project_id=projects[sc["domain"]].id, name=sc["name"], owner_id=users[sc["owner"]].id,
            status=sc["exec"].value, health_status=sc["health"].value,
            priority=sc["prio"].value, contribution_pct=sc["contrib"], is_core=sc["core"],
            tags=[Domain(sc["domain"]).name, "核心站" if sc["core"] else "长尾"],
        )
        s.add(sp)
        await s.flush()

        # 版本历史：最后一个为线上
        live_version_no = sc["versions"]
        for v in range(1, sc["versions"] + 1):
            ver = SpiderVersion(
                spider_id=sp.id, version=v,
                rules={**RULES_BASE, "_v": v},
                incremental={"field": "pub_time", "watermark_key": f"{sp.name}:wm", "window": "3d"},
                hooks=[] if sc["domain"] != Domain.ic else ["sign"],
                is_live=(v == live_version_no),
                author_id=users[sc["owner"]].id,
                change_msg=(f"v{v} 初始化规则" if v == 1 else f"v{v} 调整 selector / 字段映射"),
                created_at=now - timedelta(days=(sc["versions"] - v) * 5 + 1),
            )
            s.add(ver)
            await s.flush()
            if v == live_version_no:
                sp.current_version_id = ver.id

        # 调度
        if sc["cron"]:
            s.add(Schedule(spider_id=sp.id, cron=sc["cron"], queue="default",
                           jitter_sec=30, enabled=(sc["exec"] != SpiderExecStatus.disabled)))

        # 运行历史：近 10 次。最近一次用剧本信号；历史用基线（健康站有新增）以撑趋势柱图。
        sr = sc["sr"]
        for k in range(10):
            ts = now - timedelta(hours=k * 6 + 1)
            is_latest = (k == 0)
            if is_latest and sc["sig"] is not None:
                signals = sc["sig"]
            elif sc["sig"] is None:
                signals = {kk: None for kk in SIGNAL_KEYS}
            else:
                # 历史基线：按健康站给出新增，干涸/故障站历史也曾正常（撑断崖叙事）
                base_rows = sc["sig"].get("list_rows") or 40
                base_new = 18 + (k % 5) * 6  # 历史有数据
                signals = _sig(rows=base_rows or 40, fill=0.96, new=base_new,
                               dup=max(0, base_rows - base_new) if base_rows else 10, wm=True)
            # 执行态：按 success_rate 掺入个别 failed
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
                stats={"note": sc.get("note", "")}, signals=signals,
                created_at=ts,
            ))

    await s.commit()
