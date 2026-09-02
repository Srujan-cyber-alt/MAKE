"""add_vision_analyses_table

Revision ID: 004
Revises: 003_add_transformation_tables
Create Date: 2026-09-02

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

# revision identifiers, used by Alembic.
revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'vision_analyses',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('project_id', UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('asset_id', UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('user_id', UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('analysis_type', sa.String(50), nullable=False),
        sa.Column('backend', sa.String(50)),
        sa.Column('progress', sa.Float, server_default='0.0'),
        sa.Column('result_summary', JSONB),
        sa.Column('error', sa.Text),
        sa.Column('frames_analyzed', sa.Integer, server_default='0'),
        sa.Column('started_at', sa.Float),
        sa.Column('completed_at', sa.Float),
        sa.Column('created_at', sa.Float, server_default=sa.text('EXTRACT(epoch FROM now())')),
        sa.Column('updated_at', sa.Float, server_default=sa.text('EXTRACT(epoch FROM now())')),
    )
    op.create_index('ix_vision_analyses_project_id', 'vision_analyses', ['project_id'])
    op.create_index('ix_vision_analyses_asset_id', 'vision_analyses', ['asset_id'])
    op.create_index('ix_vision_analyses_user_id', 'vision_analyses', ['user_id'])
    op.create_index('ix_vision_analyses_status', 'vision_analyses', ['status'])


def downgrade():
    op.drop_index('ix_vision_analyses_status', table_name='vision_analyses')
    op.drop_index('ix_vision_analyses_user_id', table_name='vision_analyses')
    op.drop_index('ix_vision_analyses_asset_id', table_name='vision_analyses')
    op.drop_index('ix_vision_analyses_project_id', table_name='vision_analyses')
    op.drop_table('vision_analyses')
