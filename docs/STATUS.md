# 项目进度 STATUS

> 给后续会话/另一台开发机：当前到哪了、什么已验证、下一步做什么。每个里程碑完成后更新本文件。

最后更新：2026-06-25（M0 完成）

---

## 里程碑总览

| # | 里程碑 | 状态 | 验收标准 |
|---|---|---|---|
| **M0** | 骨架 + 基础设施 | ✅ 完成并验证 | 三端跑通互通；主链路全绿 |
| M1 | 数据模型 + 核心 CRUD | ⏳ 下一步 | 能建爬虫、查列表、看详情；前端对齐高保真+登录页 |
| M2 | 规则编辑器 + 试运行 | 未开始 | URL+规则→async引擎抓首页→字段JSON+四层信号 |
| M3 | 调度 + 执行 + 落库 | 未开始 | Beat(抖动)→worker执行→幂等入库；Run状态机+signals |
| M4 | 实时 + 分诊看板 | 未开始 | worker→Redis→WS→深色分诊看板看真实健康三态 |

---

## M0 已完成内容（已 commit + push GitHub main）

**结构**：monorepo `backend / worker / frontend / shared` + docker-compose + Dockerfile + docs。

**已建并验证**：
- 7 张表 + alembic baseline 迁移：`projects / users / spiders / spider_versions / runs / schedules / dedup_registry`
- 3 个硬约束就位：`runs.signals`(四层信号必存) / `spider_versions.rules`(配置入库JSONB) / `spiders` 执行态≠健康态(+priority/contribution_pct/is_core)
- backend：`/health`、`GET /api/projects`、爬虫 CRUD、`POST /api/spiders/{id}/run`、WS `/ws/triage`、启动幂等 seed 默认 project+user
- worker：celery(late-ack + prefetch=1 防丢数据)、`worker.ping_run`(写 Run+占位四层信号 + 发 Redis pub-sub)、sink/reporter 契约骨架
- frontend：Vue3 深色控制台 shell + Triage 页(主链路自检按钮 + WS 实时流)

**终验主链路（在 sh-2c2g 实测全绿）**：
建 Spider → 入 PG → `POST /run` → worker 收到 → 写 Run(success, http_status=200) → 发 Redis CH_TRIAGE → 订阅抓到 `{"type":"run_done",...}`。

**过程踩坑记录（已修，避免重犯）**：
1. Dockerfile 用 build-essential 编译 → 2c2g 上 30min 卡死。改用 `psycopg[binary]`/`asyncpg` 预编译 wheel + 清华 pip 源 → 25 秒起栈。
2. Celery 生产端发到默认队列 `celery`、worker 配 `task_default_queue="default"` 消费 → 队列名不匹配任务不执行。M0 统一用默认队列（M3 再引入命名队列 default/high/retry/low）。

---

## 测试/部署机

- `ssh sh-2c2g`：Ubuntu 24.04，2核1.6G，已装 Docker/Compose/Python3.12/Node22/git。代码在 `~/spiderx`。
- 当前 4 容器在线：backend(8000)/postgres(5432)/redis(6379)/worker。
- ⚠️ 该机内存小：**重型池 Scrapy/Playwright/Chromium 别在此跑**；前端 dev 在本地跑；真实并发/压测等加大机器。

---

## 下一步：M1

详细落地见 **`docs/M1前端落地要点.md`**（已读完高保真，沉淀了 token + 组件清单 + 构建顺序 + 后端契约）。
`frontend/src/theme/tokens.css` 已按高保真精确令牌实装（深色控制台 + 三套字体 + 健康三态色 + keyframes）。

M1 范围：登录页 + App Shell + 爬虫列表 + 爬虫详情 + 版本管理（巡检/规则/调度/作者等屏 M2~M4）。
- 后端补：`GET /api/spiders/:id`、`PATCH`、`/versions`、`/versions/diff`、`/rollback`、`/runs`、列表筛选分页。
- 前端：先 theme+原子组件(StatusDot/HealthBadge/ExecBadge/Panel/KpiCard/CtaButton/Pill) → AppShell → Login → Spiders → Detail → Versions。
- 健康/四层信号 M1 用占位/unknown 渲染（真实引擎 M2/M3 才产出），但组件按真实契约写。
完成后更新本文件 + commit/push。
