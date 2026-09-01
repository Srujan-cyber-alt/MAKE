"""Phase 6: Add transformation tables and Job columns

Revision ID: 003
Revises: 002
Create Date: 2026-09-01
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("transformation_id", sa.String(36), nullable=True))
    op.add_column("jobs", sa.Column("parent_job_id", sa.String(36), sa.ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True))
    op.add_column("jobs", sa.Column("stage", sa.String(50), nullable=True))
    op.add_column("jobs", sa.Column("progress", sa.Float(), nullable=False, server_default="0"))
    op.create_index("ix_jobs_transformation_id", "jobs", ["transformation_id"])
    op.create_index("ix_jobs_parent_job_id", "jobs", ["parent_job_id"])

    op.create_table(
        "transformations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_asset_id", sa.String(36), sa.ForeignKey("assets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("result_asset_id", sa.String(36), sa.ForeignKey("assets.id", ondelete="SET NULL"), nullable=True),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("operations", sa.JSON(), nullable=False),
        sa.Column("plan", sa.JSON(), nullable=True),
        sa.Column("references", sa.JSON(), nullable=True),
        sa.Column(
            "status",
            sa.Enum("pending", "analyzing", "planning", "queued", "processing",
                    "completed", "failed", "cancelled", name="transformationstatus"),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("progress", sa.Float(), nullable=False, server_default="0"),
        sa.Column("current_stage", sa.String(50), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("result_metadata", sa.JSON(), nullable=True),
        sa.Column("idempotency_key", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_transformations_project_id", "transformations", ["project_id"])
    op.create_index("ix_transformations_user_id", "transformations", ["user_id"])
    op.create_index("ix_transformations_source_asset_id", "transformations", ["source_asset_id"])
    op.create_unique_constraint("uq_transformations_idempotency_key", "transformations", ["idempotency_key"])

    op.create_table(
        "transformation_operations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("transformation_id", sa.String(36), sa.ForeignKey("transformations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("operation_type", sa.String(50), nullable=False),
        sa.Column("target", sa.JSON(), nullable=True),
        sa.Column("parameters", sa.JSON(), nullable=False),
        sa.Column("references", sa.JSON(), nullable=True),
        sa.Column("preserve_identity", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("preserve_background", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("strength", sa.Float(), nullable=False, server_default="0.8"),
        sa.Column("seed", sa.Integer(), nullable=True),
        sa.Column("frame_range", sa.JSON(), nullable=True),
        sa.Column("depends_on", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_transformation_operations_transformation_id", "transformation_operations", ["transformation_id"])

    op.create_table(
        "transformation_masks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("transformation_id", sa.String(36), sa.ForeignKey("transformations.id", ondelete="CASCADE"), nullable=True),
        sa.Column("asset_id", sa.String(36), sa.ForeignKey("assets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("mask_type", sa.String(50), nullable=False),
        sa.Column("frame_range", sa.JSON(), nullable=True),
        sa.Column("feather", sa.Float(), nullable=False, server_default="2.0"),
        sa.Column("expand", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("invert", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("storage_dir", sa.String(512), nullable=True),
        sa.Column("frame_paths", sa.JSON(), nullable=True),
        sa.Column("mask_metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_transformation_masks_transformation_id", "transformation_masks", ["transformation_id"])
    op.create_index("ix_transformation_masks_asset_id", "transformation_masks", ["asset_id"])


def downgrade() -> None:
    op.drop_index("ix_transformation_masks_asset_id", table_name="transformation_masks")
    op.drop_index("ix_transformation_masks_transformation_id", table_name="transformation_masks")
    op.drop_table("transformation_masks")

    op.drop_index("ix_transformation_operations_transformation_id", table_name="transformation_operations")
    op.drop_table("transformation_operations")

    op.drop_constraint("uq_transformations_idempotency_key", "transformations", type_="unique")
    op.drop_index("ix_transformations_source_asset_id", table_name="transformations")
    op.drop_index("ix_transformations_user_id", table_name="transformations")
    op.drop_index("ix_transformations_project_id", table_name="transformations")
    op.drop_table("transformations")
    op.execute("DROP TYPE IF EXISTS transformationstatus")

    op.drop_index("ix_jobs_parent_job_id", table_name="jobs")
    op.drop_index("ix_jobs_transformation_id", table_name="jobs")
    op.drop_column("jobs", "progress")
    op.drop_column("jobs", "stage")
    op.drop_column("jobs", "parent_job_id")
    op.drop_column("jobs", "transformation_id")