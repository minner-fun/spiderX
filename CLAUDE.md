# CLAUDE.md — SpiderX（Arachne）项目上下文

> 本文件给 Claude Code 自动加载。读完它 + `docs/` 即可无缝接续开发。
> 详细设计见 `docs/SpiderX设计纲要-v1.md`、背景见 `docs/项目背景与设计沉淀.md`、进度见 `docs/STATUS.md`。

---

## 1. 这是什么

**SpiderX（设计代号 Arachne）** = 面向内部工程团队的**分布式爬虫管理平台**。核心场景：在 2000+ 爬虫规模下，快速回答「今天谁出问题了，且是『网站改版挂了』还是『真的没新数据』」，并把爬虫从「一堆代码文件」变成「库里的配置 + 可自动分诊的受管资产」。

**一句话理念**：把「爬虫=代码文件 + 全靠消息队列当真相源 + 人盯人」换成「爬虫=库里的配置 + Run 记录当真相源 + 自动分诊」。

**立身之处**（复盘 6 个真实旧项目得出，没有任何一个同时具备这三样）：
1. **配置即数据**（简单站不写代码）
2. **成熟 worker 框架**（下载/解析/sink 分离）
3. **管理平面**（调度/健康分诊/版本/多租户/作者考评）
SpiderX = 这三者的交集。

---

## 2. 技术栈（已锁定，勿擅改）

| 层 | 选型 |
|---|---|
| 后端/控制平面 | FastAPI + SQLAlchemy 2.0(async) + Alembic + Pydantic v2 |
| 元数据库 | PostgreSQL（多租户 project_id + 行级隔离）|
| 调度/队列/实时 | Celery + Celery Beat + Redis（broker / pub-sub / 指标 / 队列水位 / 去重）|
| 爬虫引擎 | 轻量池 asyncio+httpx（配置驱动）；重型池 Scrapy/Playwright（代码驱动）|
| 前端 | Vue 3 + TS + Vite + Pinia + ECharts，深色控制台主题 |
| 仓结构 | Monorepo：`backend / worker / frontend / shared` |
| 日志/信号 | MVP 进 PG（带 sink 抽象），上量切 ClickHouse |

---

## 3. 架构支柱（开发时必须守住的设计决策）

1. **爬虫两档 + 衔接**：配置驱动为主（覆盖 2000 同质简单站）+ 可插拔代码钩子（兜住少数复杂站）。按 **URL 正则 → 抽取规则** 路由（借鉴 Sardinia 框架）。
2. **worker 执行器 4 角色**：JobSource（任务源）/ Downloader（怎么抓）/ Processor（怎么解析，URL 路由）/ Sink（怎么落）。两个池：轻量 async 池 / 重型隔离池。
3. **健康分诊（核心差异点）**：不只看最终条数，看**四层信号** HTTP→列表命中行数→必填字段抽到率→去重后新增条数，才能区分「改版挂了 🔴」vs「真没数据 🟡」vs「健康 🟢」vs「未上报 ⚪」。`runs.signals` 是硬约束、唯一真相源。
4. **核心站盯梢**：~20 站贡献 80% 数据；business_value = max(手填 priority, 自动 contribution_pct)；核心站干涸按小时判、长尾按天。
5. **并发天花板是代理不是计算**：代理双 driver（池模式/隧道模式）+ IP 感知并发管控；L4 单域名礼貌限速最致命（政府站默认 1~2 并发+1~3s）；调度抖动防惊群。
6. **统一 Sink**：抓取与入库解耦，幂等 upsert 去重；可插拔多目标（MVP 默认 PG，可换 mysql/kafka）。
7. **可靠性**：执行成功才 ack（late-ack，防丢数据）+ 有界预取 + DLQ + Run 记录对账（已分发未完成可见）。重试有界，**绝不 resend 给自己**。
8. **治理**：配置入库 + SpiderVersion 版本化（diff/回滚，根除复制文件当版本）；新建查重防冒充；作者考评=去重后持续出数据的站点数；集中密钥（env，无 local=True 开关）。
9. **双去重闸门**：入队去重（防队列爆炸）+ 已采去重，平台原语带自动 TTL。
10. **反爬剥离**：验证码/sign 破解走外部服务 + JS-exec 钩子（沙箱，能读 cookie 上下文）；凭据/cookie 池 sticky/random + 异步刷新旁路。

> 这些决策都是从 6 个旧项目的痛/经验逼出来的，不是拍脑袋。背景见 `docs/项目背景与设计沉淀.md`。

---

## 4. 当前进度

**M0 已完成并验证（见 `docs/STATUS.md`）**：monorepo 骨架 + docker-compose + 7 表 + alembic + 三端跑通。终验主链路全绿：建 Spider → 入 PG → 触发 run → worker 写 Run(四层信号) → Redis pub-sub → WS 转发。

**M1 已完成并验证**：登录 + App Shell + 爬虫列表/详情/版本 5 屏对齐 `design_handoff_hifi/` 高保真；后端补齐爬虫接口(列表筛选分页/详情/PATCH/版本/diff/回滚/运行) + 多域多健康态 demo seed。四层信号判定、「成功率≠健康」叙事、版本 diff/回滚均落地。

**M2 已完成并验证**：配置驱动 async 引擎(`worker/engine/core.py`：httpx+parsel，URL 路由+transform)**首次产出真实四层信号**；本地 fixture 仿真页 + 试运行/取页接口；三栏规则编辑器(页面预览点选高亮→生成 selector / 字段映射 / 抓取配置)，保存=生成新版本。

**M3 已完成并验证**：真实执行闭环 —— `run_spider` 引擎抓取→**统一 Sink 幂等 upsert(`crawled_records`)→真实 L4 `dedup_new`**→`shared/health.py` 更新 health_status→推 triage；**双去重闸门**区分「出数据🟢 vs 真没数据🟡」。Celery Beat(`dispatch_due` croniter+抖动 / `reconcile` 扫已分发未完成) + 调度·对账屏(gantt+队列水位+对账)。seed 改规则一致(broken🔴/blocked🔴/dry🟡/ok🟢/code⚪)，健康由引擎实测。

**里程碑**：M0✅ → M1✅ → M2✅ → M3 调度+执行+落库✅ → M4 实时+分诊看板。**下一步：M4**（M2.5 新建查重向导从 M2 拆出，可穿插）。

---

## 5. 怎么跑起来（另一台机器 clone 后）

```bash
# 1. 配置环境
cp .env.example .env          # 按需改密钥；容器内用服务名 postgres/redis 即可

# 2. 起后端栈（需要 Docker）
docker compose up -d --build  # pg + redis + backend + worker
curl localhost:8000/health    # {"status":"ok","db":true,"redis":true}

# 3. 前端本地 dev（前端不进 compose，省内存）
cd frontend && npm install
VITE_API_TARGET=http://<后端地址>:8000 npm run dev   # 打开 localhost:5173

# 数据库迁移：backend 容器启动时自动 alembic upgrade head
# 新增迁移：docker compose exec backend alembic -c backend/alembic.ini revision --autogenerate -m "msg"
```

测试/部署机：`ssh sh-2c2g`（Ubuntu 2c2g，已装 Docker；代码在 `~/spiderx`）。注意：**重型池 Scrapy/Playwright 别在 2c2g 跑**（内存不够），等加大机器。

---

## 6. 约定 / 工作方式

- **配置优先于代码**：能做成配置的别写死成代码。
- **绝不硬编码密钥/连接**：一律走 env；禁止 `local=True` 这类全局开关（旧项目教训）。
- **Run 必带 signals**：任何爬虫（配置/代码驱动）都要回报四层信号，缺层=null=unknown。
- **配置即版本**：改爬虫走 SpiderVersion，禁止复制文件当版本。
- **小阶段提交 GitHub**：每个里程碑/可验证节点 commit + push。commit message 末尾带
  `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`。
- **占位数据用真实域**：招投标 / IC 元器件 / 电商 / 招聘。
- 设计稿：`爬虫管理系统设计/`(v1) + `design_handoff_v3/`(lofi 定稿) + `design_handoff_hifi/`(高保真+登录页)。视觉走深色控制台。

---

## 7. 文档地图
- `docs/SpiderX设计纲要-v1.md` — 完整架构（13 节）
- `docs/M0实施清单.md` — M0~M4 里程碑 + M0 细节
- `docs/项目背景与设计沉淀.md` — 6 个旧项目复盘 + 所有设计决策的来龙去脉
- `docs/M1前端落地要点.md` — 高保真落地：M1 范围/组件清单/构建顺序/后端契约
- `docs/STATUS.md` — 当前进度、已验证内容、下一步
- 视觉令牌权威源：`design_handoff_hifi/README.md` + `frontend/src/theme/tokens.css`
