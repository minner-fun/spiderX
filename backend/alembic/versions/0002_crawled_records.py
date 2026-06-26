"""M3：业务落库表 crawled_records（统一 Sink 目标 + 已采去重闸门）。

Revision ID: 0002_crawled_records
Revises: 0001_init
Create Date: 2026-06-26
"""
from alembic import op
from sqlalchemy import inspect

from shared.models import CrawledRecord

revision = "0002_crawled_records"
down_revision = "0001_init"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    # 0001 用 create_all(从模型元数据建全部表)；新库已含本表则跳过，旧库则补建。
    if "crawled_records" not in inspect(bind).get_table_names():
        CrawledRecord.__table__.create(bind)


def downgrade() -> None:
    bind = op.get_bind()
    if "crawled_records" in inspect(bind).get_table_names():
        CrawledRecord.__table__.drop(bind)
