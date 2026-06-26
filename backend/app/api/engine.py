"""M2 引擎接口：fixture 页 + 试运行(dry-run) + 取页 HTML(供编辑器点选预览)。
试运行无状态（不需要 spider），编辑器实时调用。"""
from __future__ import annotations
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from backend.app import fixtures
from worker.engine.core import dry_run, fetch

router = APIRouter(prefix="/api", tags=["engine"])


def _resolve(url: str) -> str:
    """相对 fixture 路径（/api/fixtures/..）→ 容器内可达的绝对地址。"""
    if url.startswith("/"):
        return f"http://localhost:8000{url}"
    return url


def _guard(url: str):
    p = urlparse(_resolve(url))
    if p.scheme not in ("http", "https"):
        raise HTTPException(400, "仅支持 http/https")


# —— fixture 页（仿真站，离线确定性）——
@router.get("/fixtures/{name}", response_class=HTMLResponse)
async def get_fixture(name: str):
    html = fixtures.render(name)
    if html is None:
        raise HTTPException(404, "fixture not found")
    return HTMLResponse(html)


@router.get("/engine/default-rules")
async def default_rules():
    """编辑器新建/重置用的默认规则模板（匹配 bid fixture）。"""
    return fixtures.DEFAULT_RULES_BID


class FetchPageIn(BaseModel):
    url: str


@router.post("/engine/fetch-page")
async def fetch_page(body: FetchPageIn):
    """取目标页 HTML，供编辑器渲染预览 + 点选生成 selector。服务端抓取，规避浏览器 CORS。"""
    _guard(body.url)
    status, html = await fetch(_resolve(body.url))
    return {"status": status, "html": html if status == 200 else ""}


class DryRunIn(BaseModel):
    url: str
    rules: dict


@router.post("/engine/dry-run")
async def engine_dry_run(body: DryRunIn):
    """配置 + URL → 抓首页 → 抽字段 + 真实四层信号（L1 HTTP / L2 list_rows / L3 fill_rate）。"""
    _guard(body.url)
    return await dry_run(_resolve(body.url), body.rules)
