"""Add result_json to query_logs

Revision ID: 002
Revises: 001
Create Date: 2026-04-08
"""
from alembic import op
import sqlalchemy as sa

revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('query_logs', sa.Column('result_json', sa.Text, nullable=True))


def downgrade() -> None:
    op.drop_column('query_logs', 'result_json')
