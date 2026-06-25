"""Alembic 环境：同步引擎，URL 从环境变量读取，metadata 来自 shared.models。"""
from logging.config import fileConfig
from alembic import context
from sqlalchemy import create_engine

from shared.db import Base, sync_url
import shared.models  # noqa: F401  注册所有表到 Base.metadata

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_online() -> None:
    engine = create_engine(sync_url(), future=True)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()


run_migrations_online()
