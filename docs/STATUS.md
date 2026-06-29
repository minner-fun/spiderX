# 项目进度 STATUS

> 给后续会话/另一台开发机：当前到哪了、什么已验证、下一步做什么。每个里程碑完成后更新本文件。

最后更新：2026-06-27（M4 完成 · 本期主线 M0→M4 全部达成）

---

## 换机接续：另一台机器从这里继续

> 本期主线 M0→M4 已全部完成并 push 到 `origin/main`（迁移到 0003）。换机后按下面起栈即可继续。

```bash
git clone <repo> && cd spiderX
cp .env.example .env                  # 按需改密钥；容器内用服务名 postgres/redis
docker compose up -d --build          # pg + redis + backend + worker（首次 build 约 1~2 分钟）
curl localhost:8000/health            # {"status":"ok","db":true,"redis":true}
cd frontend && npm install
VITE_API_TARGET=http://localhost:8000 npm run dev   # 打开 localhost:5173
```

- **首启自动**：backend 容器启动跑 `alembic upgrade head`（建表到 0003）+ 幂等 `seed_demo`（空库才插：2 项目 + 81 站 demo）。worker 含 Beat，每分钟按 cron 自动跑到点的爬虫。
- **登录**：M1 假登录，账号/密码随便填 → 默认进巡检分诊看板。
- **端口冲突（5432）**：若本机已占 5432，建一个 `docker-compose.override.yml`（已 gitignore，不提交）把容器 PG 宿主映射改到别的端口，用 `!override` 替换 ports（compose 对 ports 是追加合并，必须用 `!override`）：
  ```yaml
  services:
    postgres:
      ports: !override ["5433:5432"]
  ```
  容器之间仍走服务名 `postgres:5432`，不受宿主映射影响。本机(minner dev)用的就是 5433，见文末「测试/部署机」。
- **停服**：`docker compose down`（保留数据卷 `spiderx_pgdata`）｜`docker compose down -v`（连数据一起清，下次起栈重新 seed）。前端 dev 直接 Ctrl-C。
- **重型池**（Scrapy/Playwright）别在小内存机跑；M0~M4 全是轻量 async（httpx+parsel），无所谓。

**接续开发的下一步**：见文末「下一步」——M5（实时·节点 / 告警·反爬）或 M2.5（新建查重向导）。读完本文件 + `CLAUDE.md` + `docs/SpiderX设计纲要-v1.md` 即可无缝接续。

---

## 里程碑总览

| # | 里程碑 | 状态 | 验收标准 |
|---|---|---|---|
| **M0** | 骨架 + 基础设施 | ✅ 完成并验证 | 三端跑通互通；主链路全绿 |
| **M1** | 数据模型 + 核心 CRUD | ✅ 完成并验证 | 登录 + 外壳 + 列表/详情/版本 5 屏对齐高保真；后端接口 + 多域 seed |
| **M2** | 规则编辑器 + 试运行 | ✅ 完成并验证 | 配置驱动 async 引擎抓首页→字段JSON+**真实四层信号**；三栏编辑器(点选高亮) |
| M2.5 | 新建查重向导 | 未开始 | 7 步向导 + domain/url_pattern/字段重合度撞库拦截（从 M2 拆出）|
| **M3** | 调度 + 执行 + 落库 | ✅ 完成并验证 | Beat(croniter+抖动)→worker真实执行→Sink幂等upsert→**真L4 dedup_new**+双去重闸门+对账 |
| **M4** | 实时 + 分诊看板 | ✅ 完成并验证 | worker→Redis→WS→深色分诊看板(三态/核心站/热力图/分诊队列/🟡闭环)看真实健康 |
| M5 | 实时·节点 / 告警·反爬 | 未开始 | 吞吐视图 + 节点控制台 + 告警规则 + 反爬面板（IA 已规划）|

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

## M2 已完成内容（已 commit GitHub main，2026-06-26）

**第一次产出真实四层信号**——配置驱动 async 引擎从 URL+规则抓首页、抽字段、报信号。

**后端引擎**（`worker/engine/core.py`，backend 与 worker 共用）：
- `fetch`(httpx async) → URL 正则 `route` 到 processor → `parse_list`(parsel CSS) → `apply_transform`(text/int/money 万元→元/date 归一/area)。
- 真实四层信号：L1 `http_status` / L2 `list_rows`(命中行数) / L3 `field_fill_rate`(字段抽到率)；L4 `dedup_new` 试运行=null（真实去重在 M3 执行落库时产出）。
- `backend/app/fixtures.py`：仿真招投标/IC 列表页 HTML（离线确定性验证）+ 匹配的默认规则模板；seed 规则已对齐 fixture，seeded 爬虫规则可直接试运行。
- 接口（`backend/app/api/engine.py`）：`GET /api/fixtures/:name`、`GET /api/engine/default-rules`、`POST /api/engine/fetch-page`(预览取页)、`POST /api/engine/dry-run`(试运行)。
- 规则存取（`api/spiders.py`）：`GET /api/spiders/:id/rules`(加载线上配置)、`POST /api/spiders/:id/rules`(保存=生成新版本，配置即版本)。

**前端规则编辑器**（`views/Rules.vue`，三栏）：
- 顶部 URL 栏 + 可视化/代码模式切换 + ▶试运行 + 保存并试运行。
- **页面预览**：`fetch-page` 取 HTML → iframe `srcdoc`(sandbox=allow-scripts) 注入 picker：hover 高亮 + click→计算 leaf selector→`postMessage` 回填。
- **字段映射**：name/type/selector/attr 增删 + 逐字段「拾取」。
- **抓取配置**：增量字段/水位窗口/代码钩子 + 重置默认模板。
- **试运行结果**：复用 `utils/health.ts` 四层信号判定 + 抽取记录样本 JSON。

**验证**：`vue-tsc` + 生产 `npm run build` 通过；puppeteer 端到端(点选拾取 row→`div.notice-item`、试运行 L1/L2/L3 真信号、保存 v3→v4)；引擎 curl 异常态(错误 selector→list_rows 0 结构故障 / 缺字段→fill 0.5)；chrome 截图核对三栏。

> 注：fetch-page/dry-run 是服务端抓取（规避浏览器 CORS），属内部工具，存在 SSRF 面，仅限内网；已限制 http/https。

---

## M3 已完成内容（已 commit GitHub main，2026-06-26）

**真实执行闭环 + 健康从真信号驱动**——把 M2 引擎接进 Celery，产出真实 L4 `dedup_new`，让「🔴改版 / 🟡真没数据 / 🟢健康 / ⚪未上报」由引擎实测而非 seed 假数据。

**执行管线**：
- `worker/tasks.py run_spider`：fetch(引擎)→parse→**统一 Sink 幂等 upsert**→真实四层信号(含 L4 `dedup_new`/`duplicate`/`watermark_hit`)→Run 状态机(running→success/failed)→`shared/health.py verdict` 更新 `spider.health_status`→推 triage。trigger `/run` 改派 `run_spider`(真实执行)。
- `worker/sink/pg.py PgSink`：`crawled_records` 表 `(spider_id,dedup_key)` 唯一 = **已采去重闸门**；实插入数 = 真 `dedup_new`。`models.CrawledRecord` + `0002` 迁移。
- **验证**：1 次跑 dedup_new=12/healthy/落库12；2 次跑 dedup_new=0/duplicate=12/data_dry（双去重闸门区分「出数据 vs 真没数据」）。

**调度 + 对账**（`worker/celery_app.py beat_schedule`）：
- `dispatch_due`(60s)：croniter 扫 Schedule cron 到点 → enqueue `run_spider`，`countdown` 抖动防惊群，`last_run_at` 作下发水位。
- `reconcile`(120s)：扫 queued/running 超 10min 的 Run → 标 stopped（防 IC 那种静默丢数据，Run 记录作真相源）。
- `api/schedule.py GET /overview`：调度时间线(croniter 未来 24h 触发点) + 对账(已分发/进行/完成/stuck/dlq) + 队列水位(redis llen)。

**前端调度·对账屏**（`views/Schedule.vue`）：对账 KPI×5 + 24h gantt 时间线(域着色 fire 点) + 队列水位条 + 对账叙事条，每 15s 刷新。

**seed 规则一致性**：每只爬虫 rules 跑起来就产出其「应有」健康 —— broken(错 selector)→🔴 / blocked(403)→🔴 / dry(预置 crawled)→🟡 / ok→🟢 / code(无 entries·暂停)→⚪。故 beat/手动执行印证而非破坏叙事；schedule `last_run_at=now` 防启动惊群。

**验证**：`vue-tsc` + 生产 build 通过；真实跑 4 只健康与规则一致(rows0→🔴 / new12→🟢 / new0→🟡 / 403→🔴 / 未跑→⚪)；overview/dispatch_due/reconcile curl 全绿；chrome 截图调度屏。

> 注：入队去重闸门(inque scope, DedupRegistry+TTL)在有父子任务派生(detail 子任务)时才真正吃重，M3 列表级以已采去重(crawled_records 唯一约束)为主，原语已就位。

---

## M4 已完成内容（已 commit GitHub main，2026-06-27）

**门面屏 + 实时闭环**——默认首页巡检分诊看板，看真实健康三态实时流。

**后端**（`backend/app/api/triage.py`）：
- `summary` 三态计数 / `heatmap` 全量站点格(红前黄中绿后,按价值次排) / `core-sites` 核心站盯梢(today/baseline/spark) / `queue` 分诊队列(价值×严重度, pending/snoozed/escalated) / `snooze`(确认真没数据→N天) / `escalate`(升级提P0)。
- `models.SnoozeState`(🟡闭环: snoozed/escalated/released) + `0003` 迁移；`run_spider` 出数据(转🟢)自动解除 snooze。
- seed 加 **72 只轻量舰队爬虫**(健康分布+1版本+6run sparkline, 无调度→健康为最近已知) 撑聚合视图，共 **81 站**。

**前端**（`views/Triage.vue` 替换 M0 脚手架，默认首页 `/` → `/triage`）：
- 三态计数 KPI + 核心站盯梢(sparkline 卡) + 全量热力图(可点进详情) + 四层信号模型条 + 分诊队列(🟡 条目带「✓确认真没数据 / ↑升级故障」按钮 + snooze 闭环说明) + **WS 实时事件流**(LIVE 绿脉冲)。
- `components/Sparkline.vue`(ECharts 迷你线)；`client` 6 个 triage 方法。

**实时链路**：worker `run_spider` → `publish_sync(CH_TRIAGE, run_done)` → Redis pub-sub → WS `/ws/triage` → 前端事件流 + 看板刷新。**验证**：Triage 页触发运行 → 事件流实时收到「中国政府采购网-中央 · 结构故障 · 新增 0」。

**验证**：`vue-tsc` + 生产 build 通过；summary🔴2🟡4🟢74⚪1；snooze 把 data_dry 移出 pending、escalate→escalated；WS 端到端实时流；chrome 全屏截图核对看板。

---

## 已知待补 / 技术债（M0→M4 设计 review 沉淀，2026-06-27）

> 这些是**待补清单不是返工清单**——主线架构已对齐设计纲要 10 条支柱，下面是按当前 scope 合理推迟、或需在对应阶段补齐的点。Review 详见对话；逐条标了触发时机。

**架构演进决策（已偏离纲要但合理，需知晓）**
- **健康做成「事件驱动」而非「周期巡检批」**：现状每次 `run_spider` 即时更新 `spider.health_status`（简单、MVP 够用）；纲要 §5 设想的是周期巡检产出 `HealthSnapshot`。**后果**：以下两个 §5 能力依赖批处理层，尚未实现——
  - 核心站「**按小时** vs 长尾**按天**」差异化干涸判定（现 `verdict()` 对所有站统一：dedup_new==0 即🟡）。底层 `is_core/contribution_pct/baseline` 已就位，缺的是按 `is_core` 取时间窗的聚合逻辑。
  - **基线偏离异常检测**（平时 50/天突然 0 才报）。当前是「最近一次 dedup_new==0 即🟡」，无历史基线对比。
  - → 触发时机：当🟡噪音变多、或要做「核心站小时级告警」时，补一个周期巡检任务产出 HealthSnapshot。

**功能闸门 / 原语「已建未接」**
- **列表→详情 DAG 未吃重**：M3 只抓入口列表页，`emit:detail` 父子任务派生未实装 → **入队去重闸门**(`DedupRegistry` inque scope + TTL)原语已建但未接。触发时机：做复杂站/代码驱动档、或需要详情页二级抓取时。
- **DLQ 只到「可见」未到「重投」**：`reconcile` 把 stuck Run 标 `stopped`（可见性✅）、对账屏显示 dlq 计数，但无死信重投。触发时机：上真实并发/不稳定目标站后。
- **`watermark_hit` 是近似值**：现 `= bool(dup_count)`（有重复即当命中水位），非真「翻页翻到水位停止」。触发时机：实装真实增量翻页后修正语义。

**健壮性 / 待并发再改**
- **`PgSink` 去重用「先 SELECT + 应用层去重」而非真 `ON CONFLICT DO NOTHING`**（docstring 与实现不符）。单 worker 无碍；并发两个同站 run 可能在 flush 撞唯一约束报 IntegrityError（有唯一约束兜底不会脏数据，但会失败一次）。触发时机：worker 起并发后改成真 upsert（`INSERT ... ON CONFLICT DO NOTHING`）。

**尚未触及的支柱（正确推迟，非债）**
- 纲要 §6 **并发/代理双 driver（池/隧道）+ IP 感知并发管控**：M0→M4 全是 async 轻量配置驱动，未涉代理。M5+/上量时做。
- 纲要 §9/§10 **反爬剥离（验证码/sign 外部服务）+ 凭据/cookie 池 + JS-exec 钩子**：复杂站/代码驱动档的事，未碰是对的。

---

## 下一步：M5（实时·节点 / 告警·反爬）｜M2.5（新建查重向导）

- **M5**：实时吞吐视图(KPI+集群负载热力图+吞吐曲线+事件流) + 节点控制台 + 告警规则(分层信号条件) + 反爬面板(HTTP 状态码柱+验证码/封禁信号)。
- **M2.5**（从 M2 拆出）：新建爬虫 7 步向导 + 查重（domain/url_pattern/字段重合度撞库拦截）。
- 二期：RBAC 细化、结果浏览/数据导出、节点/代理池/并发配额屏（纲要 §12）。
- 详见 `docs/SpiderX设计纲要-v1.md` §6/§9/§12。完成后更新本文件 + commit/push。
