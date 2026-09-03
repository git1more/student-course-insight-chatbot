"""Initial schema with pgvector

Revision ID: 001
Revises:
Create Date: 2026-04-02
"""
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')

    op.create_table(
        'users',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('role', sa.String(50), nullable=False, server_default='user'),
        sa.Column('created_at', sa.DateTime, server_default=sa.text('now()')),
    )
    op.create_index('ix_users_email', 'users', ['email'])

    op.create_table(
        'feedback_comments',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('comment_id', sa.String(50), nullable=False, unique=True),
        sa.Column('program', sa.String(255), nullable=False),
        sa.Column('year', sa.String(10), nullable=False),
        sa.Column('comment_text', sa.Text, nullable=False),
        sa.Column('embedding', Vector(1536), nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.text('now()')),
    )
    op.create_index('ix_feedback_program_year', 'feedback_comments', ['program', 'year'])

    op.create_table(
        'query_logs',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id'), nullable=False),
        sa.Column('question', sa.Text),
        sa.Column('course_code', sa.String(255)),
        sa.Column('term', sa.String(50), nullable=True),
        sa.Column('duration_ms', sa.Integer, server_default='0'),
        sa.Column('result_count', sa.Integer, server_default='0'),
        sa.Column('status', sa.String(50), server_default='success'),
        sa.Column('created_at', sa.DateTime, server_default=sa.text('now()')),
    )
    op.create_index('ix_query_logs_user_id', 'query_logs', ['user_id'])


def downgrade() -> None:
    op.drop_table('query_logs')
    op.drop_table('feedback_comments')
    op.drop_table('users')
