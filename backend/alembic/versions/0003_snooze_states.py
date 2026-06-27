"""M4：🟡 闭环状态表 snooze_states。

Revision ID: 0003_snooze_states
Revises: 0002_crawled_records
Create Date: 2026-06-27
"""
from alembic import op
from sqlalchemy import inspect

from shared.models import SnoozeState

revision = "0003_snooze_states"
down_revision = "0002_crawled_records"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if "snooze_states" not in inspect(bind).get_table_names():
        SnoozeState.__table__.create(bind)


def downgrade() -> None:
    bind = op.get_bind()
    if "snooze_states" in inspect(bind).get_table_names():
        SnoozeState.__table__.drop(bind)
