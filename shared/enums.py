"""跨 backend/worker 共享的枚举与契约常量。值用字符串，便于演进与排查。"""
from __future__ import annotations
import enum


class Env(str, enum.Enum):
    prod = "prod"
    staging = "staging"
    dev = "dev"


class Domain(str, enum.Enum):
    bid = "bid"            # 招投标
    ic = "ic"             # 电子元器件
    ecommerce = "ecommerce"
    jobs = "jobs"         # 招聘
    other = "other"


class SpiderExecStatus(str, enum.Enum):
    running = "running"
    paused = "paused"
    disabled = "disabled"
    failed = "failed"


class HealthStatus(str, enum.Enum):
    """健康态：与执行态分离（成功率高≠健康）。"""
    healthy = "healthy"            # 🟢
    data_dry = "data_dry"         # 🟡 数据干涸
    structural_fail = "structural_fail"  # 🔴 结构性故障
    unknown = "unknown"           # ⚪ 信号未上报


class Priority(str, enum.Enum):
    p0 = "P0"
    p1 = "P1"
    p2 = "P2"


class RunExecStatus(str, enum.Enum):
    queued = "queued"
    running = "running"
    success = "success"
    failed = "failed"
    stopped = "stopped"


class DataOutcome(str, enum.Enum):
    new = "new"     # 有新增数据
    dry = "dry"     # 跑通但无新增
    na = "na"


class RunTrigger(str, enum.Enum):
    cron = "cron"
    manual = "manual"
    api = "api"
    parent = "parent"  # 父任务派生


class DedupScope(str, enum.Enum):
    inque = "inque"     # 入队去重
    crawled = "crawled"  # 已采去重


# 四层信号的 key（Run.signals 的契约）。代码驱动爬虫须按此上报，缺层=null=unknown。
SIGNAL_KEYS = (
    "http_status",     # HTTP 层
    "list_rows",       # 列表解析层：list selector 命中行数
    "field_fill_rate",  # 详情解析层：必填字段抽到率
    "dedup_new",       # 数据层：去重后新增条数
    "duplicate",       # 去重命中（已采过）条数
    "missing_rate",    # 必填字段缺失率
    "watermark_hit",   # 是否命中增量水位正常停止
)

# Redis pub/sub 频道
CH_TRIAGE = "spiderx:triage"
CH_RUN_LOG = "spiderx:run:{run_id}:log"
CH_DASHBOARD = "spiderx:dashboard"
