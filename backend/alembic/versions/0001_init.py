"""M0 baseline：从 shared.models 元数据建全部首版表（7 表）。

Revision ID: 0001_init
Revises:
Create Date: 2026-06-25
"""
from alembic import op

from shared.db import Base
import shared.models  # noqa: F401  注册表

revision = "0001_init"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # baseline 迁移：直接按模型元数据建表，与 shared/models.py 保持同步
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
