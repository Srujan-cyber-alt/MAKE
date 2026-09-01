"""Add Phase 5 generation columns

Revision ID: 002
Revises: 001
Create Date: 2026-09-01
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("plan_id", sa.String(36), sa.ForeignKey("director_plans.id", ondelete="SET NULL"), nullable=True))
    op.add_column("jobs", sa.Column("scene_id", sa.String(100), nullable=True))
    op.add_column("jobs", sa.Column("shot_id", sa.String(100), nullable=True))
    op.add_column("jobs", sa.Column("idempotency_key", sa.String(255), nullable=True))
    op.create_index("ix_jobs_idempotency_key", "jobs", ["idempotency_key"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_jobs_idempotency_key", table_name="jobs")
    op.drop_column("jobs", "idempotency_key")
    op.drop_column("jobs", "shot_id")
    op.drop_column("jobs", "scene_id")
    op.drop_column("jobs", "plan_id")
