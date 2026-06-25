# SpiderX（Arachne）设计纲要 v1

> 本文是对前期全部讨论 + 6 个先验项目复盘的收敛，作为开发蓝本。配套：《M0实施清单.md》、设计线框 `design_handoff_v3/`。

---

## 0. 立身之处（为什么做这个）

复盘了 6 个真实项目，没有任何一个同时具备这三样：

| 能力 | 谁有 | 谁没有 |
|---|---|---|
| **配置即数据**（简单站不写代码） | modules_http（半成品） | Scrapy招投标(1485份代码)、Sardinia(手写插件) |
| **成熟 worker 框架**（下载/解析/sink 分离） | Sardinia | Muto/IC（揉成一坨） |
| **管理平面**（调度/健康/版本/多租户/作者） | 都没有 | 全部 |

**SpiderX = 这三者的交集。** 用配置驱动吃掉 2000 个同质简单站，用插件/钩子兜住少数复杂站，并补上谁都没有的管理平面（巡检分诊、版本、对账、作者考评）。

核心理念（从旧项目的痛提炼）：
> 把「爬虫=一堆代码文件 + 全靠消息队列当真相源 + 人盯人」换成「爬虫=库里的配置 + Run 记录当真相源 + 自动分诊」。

---

## 1. 技术栈（已锁定）

| 层 | 选型 |
|---|---|
| 后端/控制平面 | FastAPI + SQLAlchemy 2.0(async) + Alembic + Pydantic v2 |
| 元数据库 | PostgreSQL（多租户 project_id + 行级隔离）|
| 调度/队列/实时 | Celery + Celery Beat + Redis（broker / pub-sub / 指标 / 队列水位 / 去重）|
| 爬虫引擎 | 轻量池 asyncio+httpx（配置驱动）；重型池 Scrapy/Playwright（代码驱动）|
| 前端 | Vue 3 + TS + Vite + Pinia + ECharts，深色控制台主题 |
| 仓结构 | Monorepo（backend / worker / frontend / shared）|
| 日志/信号 | MVP 进 PG（带 sink 抽象），上量切 ClickHouse |

---

## 2. 总体架构

```
              浏览器 (Vue 深色控制台)
                 │ REST + WebSocket
          ┌──────▼───────┐   读写    ┌─────────────┐
          │  FastAPI     │◀────────▶│ PostgreSQL   │ 元数据+业务数据(MVP)
          │  控制平面     │◀──读────▶│ Redis        │ 队列/实时/去重/水位
          └──────┬───────┘          └─────────────┘
                 │ enqueue
          ┌──────▼───────┐
          │ Redis 队列    │ default/high/retry/low + DLQ
          └──┬────────┬──┘
   ┌─────────▼──┐  ┌──▼──────────┐
   │ 轻量池      │  │ 重型池       │  worker 无状态、可水平扩
   │ async引擎   │  │ Scrapy/PW   │
   └─────┬──────┘  └──────┬──────┘
         │ records+signals │
         └────────┬────────┘
            ┌─────▼─────┐
            │ Sink 层    │ 幂等upsert → PG(默认,可插拔 mysql/kafka)
            └───────────┘
   ┌────────────┐
   │ Beat 调度器 │ cron + 抖动 → enqueue（核心站按小时/长尾按天）
   └────────────┘
   ┌────────────┐  ┌────────────┐  ┌──────────────┐
   │ 巡检/探针    │  │ 对账器      │  │ 代理拉取服务   │
   │ →HealthSnap │  │ →stuck/DLQ │  │ →Redis IP池   │
   └────────────┘  └────────────┘  └──────────────┘
```

实时层：worker 上报日志/指标到 Redis pub-sub，FastAPI 经 WebSocket 推前端（`/ws/triage`、`/ws/runs/:id/logs`、`/ws/dashboard`）。

---

## 3. 爬虫模型：配置驱动 + 代码驱动（两档 + 衔接）

不是二选一，而是**配置为主 + 可插拔代码钩子**，按 URL 模式路由（借鉴 Sardinia）。

### 3.1 配置驱动（覆盖多数：2000 招投标简单站）
一份爬虫配置 = 把「每站不同的部分」从代码变成数据：
```yaml
entries:                       # 多入口（jianyu 证明需要）
  - list_url_template: "https://x/list?page={page}&begin={watermark}"
processors:                    # URL正则 → 抽取规则（Sardinia 路由模型）
  - url_reg: ".*/list.*"
    type: list
    row_selector: "div.item"
    fields: [{name,selector,type,transform}]   # transform: money/area/date...
    pagination: {param: page, stop: "命中水位 | 连续N条已采"}
    emit: detail               # 列表行 → 派生 detail 任务
  - url_reg: ".*/detail.*"
    type: detail
    fields: [...]
incremental: {field: pub_time, watermark_key: "...", window: ...}
sink: {target: pg, table: bid_notices, dedup_key: "title+pub_time"}
hooks: {sign?, parse?, paginate?, render?}     # 可选，少数站用
```
> 招投标 26 字段标准 schema、tools.py 的标准转换（sign/judge_area/judge_notice_type/get_date）、4400 行省市区表——直接复用旧 Scrapy 项目的成果。

### 3.2 代码驱动（兜住少数复杂站：jianyu/boss/IC）
当配置吃不下时（复杂 DAG、JS 签名、登录态），写代码爬虫，但**靠平台原语写得薄**：
- 显式声明 **DAG/流水线**（stages + 转移 + 旁路），不散落 send_task。
- 用平台的**双去重闸门、凭据池、JS 钩子、多 sink**（见 §7/§8/§9）。
- 通过**上报契约 SDK** 回报 records + 四层 signals（否则健康标 unknown）。

### 3.3 worker 执行器抽象（4 角色，借鉴 Sardinia）
| 角色 | 职责 |
|---|---|
| JobSource | 种子/任务来源（schedule/manual/api/父任务派生）|
| Downloader | 怎么抓（httpx / Scrapy / Playwright / 代理 / 反爬钩子）|
| Processor | 怎么解析（按 URL 正则路由到抽取规则或代码处理器）|
| Sink | 怎么落（幂等 upsert，多目标）|

两个池：**轻量 async 池**（多而轻，2000 简单站）/ **重型隔离池**（Scrapy/Playwright，复杂站）。

---

## 4. 数据模型（核心实体）

多租户：所有实体带 `project_id` + 行级隔离。

| 实体 | 关键字段 |
|---|---|
| **Project** | id, name, env(prod/staging), domain(招投标/IC/电商/招聘…) |
| **User/Member/Role** | RBAC：owner/maintainer/viewer |
| **Spider** | id, project_id, name, **owner_id**, tags[], status(exec态), **health_status**(structural_fail/data_dry/healthy/unknown), **priority**(P0/P1/P2手填), **contribution_pct**(自动), **is_core**(派生 Top贡献), default_proxy_pool_id, current_version_id |
| **SpiderVersion** | id, spider_id, version, **rules**(配置JSON), incremental{field,watermark,stop}, **hooks[]**(sign/parse/paginate/render), is_live, author_id, change_msg；**唯一版本载体,禁复制文件,支持 diff/rollback** |
| **Schedule** | id, spider_id, cron, queue, priority, enabled, next/last_run_at（下发加抖动）|
| **Run** | id, spider_id, version_id, node_id, exec_status(queued/running/success/failed/stopped), data_outcome(new>0/dry), trigger, stats, **signals{http_status, list_rows, field_fill_rate, dedup_new, duplicate, missing_rate, watermark_hit}**（每层允许 null=unknown）|
| **HealthSnapshot** | spider_id, ts, layer_signals, verdict(🔴/🟡/🟢/⚪unknown), baseline{daily_avg}, today_count；干涸窗口按 is_core 取小时/天 |
| **SnoozeState** | spider_id, reason, baseline, snooze_until, auto_release_on_data, operator |
| **DedupRegistry** | 入队去重 + 已采去重两套；按 唯一键 索引，带 TTL（替代手动清理脚本）|
| **DedupSpiderCheck** | 新建查重：domain/url_pattern/field_signature → 重合度 |
| **AuthorMetric** | author_id, unique_sites(去重), healthy_sites, alive_rate, **effective_sites(持续出数据=考评)**, dup_blocked |
| **ScheduleReconcile** | dispatched, started, completed, **stuck(已分发未完成)**, dlq_count |
| **ProxyPool/ProxyIP** | driver(pool/tunnel), size, per_ip_concurrency, ip{addr,status,banned_until,success_rate} |
| **CredentialPool** | cookie/session/token，取用模式 sticky/random，刷新钩子 |
| **AlertRule/AlertEvent** | 条件支持分层信号(list_rows==0 / missing>30% / volume<-50% baseline / dispatched-done>N) |
| **LogEntry** | run_id, ts, level, message（MVP→PG，量大→ClickHouse）|

---

## 5. 健康分诊（核心差异点）

**分层信号判定**（区分「改版挂了」vs「真没数据」）：
| 层 | 信号 | =0/异常 |
|---|---|---|
| HTTP | 列表页状态码 | 非200→挂了 |
| 列表解析 | list selector 命中行数 | 0行→改版(结构故障) |
| 详情解析 | 必填字段抽到率 | 低→详情模板挂 |
| 数据 | 去重后新增条数 | 前三正常但=0→真没数据(健康) |

判定：①②③任一异常=🔴；①②③正常且④=0多日=🟡；④>0=🟢；关键层 unknown=⚪。

**规模化**：
- 基线：异常=偏离自身基线（平时50/天突然0 vs 平时0~2/天）。
- **核心站盯梢**：~20 站贡献80%数据，干涸按小时判、最高告警、分诊看板顶部常驻。价值=max(手填priority, contribution_pct档)。
- 🟡 闭环：确认真没数据→snooze N天（出数据/到期自动解除）｜升级为故障。
- 分诊看板而非2000警报：🔴改配置 / 🟡人工确认 / 🟢健康，按 价值×严重度 排序。

**配置驱动是健康自省的前提**：平台知道 selector/必填字段才能 introspect 空结果；代码驱动须按契约上报，否则 unknown。

---

## 6. 并发与代理

**天花板是代理不是计算**（30 个滚动 IP，几十核够用）。

5 层：L1 集群调度(摊平4h防惊群) / L2 worker池(轻量async广+重型隔离) / L3 单爬虫内并发 / **L4 单域名礼貌限速(最致命,Redis令牌桶跨run共享,政府站默认1~2并发+1~3s)** / L5 资源天花板。

**代理双 driver**（平台集中管，喂反爬面板）：
- 池模式：30/min灌Redis+TTL随机取，上限≈池大小×单IP并发。便宜→政府招投标站。
- 隧道模式：每请求换IP，上限受套餐QPS。贵→反爬强的IC站。
- **IP感知并发管控器**：Redis信号量按池记在途，防超卖。

自适应 AutoThrottle：域名429/403增多自动降速。**并发配额界面可调，不碰配置文件**（根除旧 .conf 痛点）。

---

## 7. 流水线/DAG 与双去重（来自 jianyu）

- **显式 DAG**：多入口→汇流→旁路声明出来（如 search/require → detail → clean → [zoo,kfk]，撞墙→cookie旁路→重投）。不散落 send_task。
- **两道去重闸门**（平台原语，自动 TTL）：
  - 入队去重：已在队列的不再投（防队列爆炸）。
  - 已采去重：采过的不再采。
- 列表行 → 派生 detail 子任务（父子任务，显式建模）。

---

## 8. 落库 Sink（抓取与入库解耦）

抓取产出 records → 统一 Sink → 批量幂等 upsert。
- 去重在 sink 层：唯一键 upsert（REPLACE/ON CONFLICT），配合水位。
- schema 按域分（招投标26字段 / IC / 电商…）。
- **可插拔多目标**：MVP 默认 PG（业务数据与元数据同库不同表），可换 mysql/kafka，不同域可指向不同目标。
- 附件（pdf/html/image）→ 对象存储，存 filepath。

---

## 9. 反爬 / Cookie / 钩子

- **反爬剥离成外部服务**：solve_captcha()/gen_sign()，钩子调用。
- **JS-exec 钩子（沙箱）**：跑站点自己的 JS 算签名（boss `__zp_sseed__`→sign），**钩子能访问 cookie 上下文**（sign 与 cookie 耦合）。
- **凭据池**（与代理池同构）：cookie/session/token，sticky（一组请求绑同一个）/ random（池中随机取）；**异步刷新旁路**（撞墙→刷新任务→重投，jianyu captor_cookies 模式平台化）。具体获取/刷新用钩子，遇站再填。
- 钩子治理：受管/沙箱 + 版本化，**不从 DB 单元格 exec 任意串**（modules_http 的反面）。

---

## 10. 可靠性（来自 IC 丢数据实锤）

- **执行成功才 ack（late ack）** + 有界预取 + 队列 durable + **DLQ 兜底**。
- **每个分发任务库里有 Run 记录作唯一真相源** + 对账器扫「已分发但从未完成」→ 丢了立刻可见，**不可能静默消失**。
- 重试：有界（max_retries+指数退避），**绝不 resend 给自己**（旧系统雪崩根因）。
- 可靠性配置平台统一保证，不靠各项目自己记得加。

---

## 11. 治理 / 版本 / 作者考评

- **配置入库 + SpiderVersion 版本化**（diff/回滚），根除「复制文件/注释当版本」。
- **新建查重**：domain/url_pattern/field_signature 三维，撞库拦截或「仍要新建需理由+审批」。
- **作者考评**：指标=去重后能持续出数据的唯一站点数（非文件数），含查重拦截、健康/挂掉、存活率。
- **集中密钥**：环境变量 + 库内连接配置，绝不硬编码；无 `local=True` 全局开关。
- **审计轨迹**：谁/何时/建改什么/版本diff，带时间戳。

---

## 12. 二期（IA 已标规划中）
RBAC 细化、结果浏览/数据导出、节点/代理池/并发配额管理屏。主线先行。

---

## 13. 本期主线（M0→M4，详见《M0实施清单.md》）
新建向导(规则编辑器)→保存 Spider+Version→试运行(dry_run+四层信号)→cron 调度(抖动)→worker async 执行+上报→WebSocket 推分诊/运行详情→幂等入库→分诊看板看真实健康。
