# 项目进度 STATUS

> 给后续会话/另一台开发机：当前到哪了、什么已验证、下一步做什么。每个里程碑完成后更新本文件。

最后更新：2026-06-26（M1 完成）

---

## 里程碑总览

| # | 里程碑 | 状态 | 验收标准 |
|---|---|---|---|
| **M0** | 骨架 + 基础设施 | ✅ 完成并验证 | 三端跑通互通；主链路全绿 |
| **M1** | 数据模型 + 核心 CRUD | ✅ 完成并验证 | 登录 + 外壳 + 列表/详情/版本 5 屏对齐高保真；后端接口 + 多域 seed |
| M2 | 规则编辑器 + 试运行 | ⏳ 下一步 | URL+规则→async引擎抓首页→字段JSON+四层信号 |
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

### 本机开发（minner dev，2026-06-25 已重现 M0）

- 环境：Docker 29 / Compose v5 / Node 24，daemon 正常。M0 主链路全绿（health / 7 表 / 建 Spider→run→Run 四层信号→Redis `spiderx:triage` 收到 `run_done` / 前端 5173 代理透传）。
- **端口差异**：本机宿主已有一个 Postgres 占 `127.0.0.1:5432`。用 **`docker-compose.override.yml`（已 gitignore，本机专属不提交）** 以 `!override` 把容器 PG 宿主映射改到 **5433**；容器间仍走服务名 `postgres:5432` 不受影响。宿主侧调试连 `localhost:5433`。
  - 注意 compose 对 `ports` 是**追加合并**，必须用 `!override` 才能替换掉基础文件的 5432，否则两个端口都绑、仍撞 5432。
- **踩坑**：首次 `up --build` 镜像拉取进度流刷屏致命令 exit 1 中断，留下 postgres 容器未挂网络的半初始化态 → 容器内 DNS 解析 `postgres` 失败。`docker compose down` 干净重建网络即恢复（镜像/build 本身没问题）。

---

## M1 已完成内容（已 commit GitHub main，2026-06-26）

落地 5 屏 + 外壳，对齐 `design_handoff_hifi/` 高保真，深色控制台「Mission Control」。

**前端**（`frontend/src/`）：
- 原子组件 `components/`：StatusDot / HealthBadge / ExecBadge / Panel / KpiCard / Pill / CtaButton / BaselineBars(ECharts)，全部引用 `theme/tokens.css` 变量。`views/Styleguide.vue` 像素校验页。
- 外壳 `layouts/AppShell.vue`：侧栏(品牌 + 监控/管理双组 + 计数徽章 + 值班用户) + 顶栏(项目切换/env/⌘K/巡检/告警)。`nav.ts` 导航模型 + 路由归属高亮。
- `views/Login.vue` 假登录（左品牌实时 mini 控制台 + 右表单）；`router/` 嵌套路由 + `beforeEach` auth guard；`stores/` auth(token) + session(项目/env)。
- `views/Spiders.vue` 列表（左筛选 + 主表 + **成功率≠健康** 叙事黄条）；`views/SpiderDetail.vue`（头部卡 + **四层健康信号表** + 数据基线柱图 + 右栏元信息/最近运行）；`views/Versions.vue`（历史 + diff + ↶回滚）。
- `utils/health.ts` 四层信号判定（①②③异常=🔴；正常且④=0=🟡；④>0=🟢；null=⚪）。

**后端**（`backend/app/`）：
- `api/spiders.py`：列表(status/health/owner/domain/q + 分页)、详情(含最近 Run 四层信号)、PATCH、versions、versions/diff(ndiff)、rollback(=新版本不复制文件)、runs。`schemas.py` 对应出入参。
- `seed.py` 幂等 demo：2 项目(招投标 prod / IC staging) × 9 爬虫，覆盖 🔴🟡🟢⚪ 四态 + 版本链 + 10 次运行(末次断崖) + 调度。

**验证**：`vue-tsc` 全过 + 生产 `npm run build` 通过；puppeteer 端到端登录流程(未登录→guard 跳 /login→提交→落 /spiders)；接口 curl 全绿(列表/筛选/详情/diff/rollback/patch)；chrome 截图逐屏像素核对。

> 健康/四层信号 M1 由 seed 提供真实结构数据（真实引擎 M2/M3 接入），组件按真实契约写，M3 接上即可。
> 未实装屏(巡检/规则/调度/作者/实时)走 `Placeholder.vue` 占位并标里程碑。

---

## 下一步：M2（规则编辑器 + 试运行）

URL + 规则 → 轻量 async 引擎(httpx) 抓首页 → 字段 JSON + 真实四层信号；含新建查重向导。详见 `docs/SpiderX设计纲要-v1.md` §3/§7。完成后更新本文件 + commit/push。
