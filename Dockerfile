# SpiderX 通用 Python 镜像（backend + worker 共用）
# 用 psycopg[binary]/asyncpg 的预编译 wheel，无需 build-essential/libpq-dev。
FROM python:3.12-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    PIP_NO_CACHE_DIR=1

COPY requirements.txt .
# 国内源加速（这台机器在国内）
RUN pip install -i https://pypi.tuna.tsinghua.edu.cn/simple --no-cache-dir -r requirements.txt

COPY . .
