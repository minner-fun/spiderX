# SpiderX（Arachne）

面向内部工程团队的**分布式爬虫管理平台**。在 2000+ 爬虫规模下，快速回答「今天谁出问题了，且是『网站改版挂了』还是『真的没新数据』」，并把爬虫从「一堆代码文件」变成「库里的配置 + 可自动分诊的受管资产」。

> 用 Claude Code 协作开发。**新会话/新机器请先读 [`CLAUDE.md`](./CLAUDE.md)** 获取完整上下文。

## 技术栈
FastAPI · SQLAlchemy(async) · PostgreSQL · Celery · Redis · Scrapy/Playwright（重型池）· Vue3+TS（深色控制台）· Monorepo。

## 仓库结构
```
backend/    FastAPI 控制平面（API + WS + alembic）
worker/     Celery worker + 爬虫引擎 + sink
shared/     前后端/worker 共享：数据模型、枚举(含四层信号契约)、db、redis 总线
frontend/   Vue3 + Vite 深色控制台
docs/       设计纲要 / M0清单 / 项目背景与设计沉淀 / STATUS
爬虫管理系统设计/ design_handoff_v3/ design_handoff_hifi/   设计稿(lofi定稿 + 高保真+登录页)
```

## 快速开始
```bash
cp .env.example .env
docker compose up -d --build      # 起 pg + redis + backend + worker（需 Docker）
curl localhost:8000/health        # {"status":"ok","db":true,"redis":true}

# 前端本地 dev（不进 compose，省内存）
cd frontend && npm install
VITE_API_TARGET=http://<后端地址>:8000 npm run dev
```

## 当前进度
**M0 完成**（骨架 + 三端跑通 + 主链路验证）。下一步 M1。详见 [`docs/STATUS.md`](./docs/STATUS.md)。

## 文档
- [`CLAUDE.md`](./CLAUDE.md) — Claude Code 上下文（必读）
- [`docs/SpiderX设计纲要-v1.md`](./docs/SpiderX设计纲要-v1.md) — 完整架构
- [`docs/项目背景与设计沉淀.md`](./docs/项目背景与设计沉淀.md) — 6 个旧项目复盘 + 决策来龙去脉
- [`docs/M0实施清单.md`](./docs/M0实施清单.md) — 里程碑与 M0 细节
- [`docs/STATUS.md`](./docs/STATUS.md) — 进度
