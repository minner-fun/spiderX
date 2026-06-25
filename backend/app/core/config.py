"""后端配置：全部从环境变量读取，绝不硬编码密钥，无 local=True 开关。"""
from __future__ import annotations
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    ENV: str = "dev"
    DATABASE_URL: str
    DATABASE_URL_SYNC: str | None = None
    REDIS_URL: str = "redis://redis:6379/0"
    CELERY_BROKER_URL: str = "redis://redis:6379/1"
    SECRET_KEY: str = "change_me"


settings = Settings()
