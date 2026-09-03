"""Fix user_id FK in query_logs to include ON DELETE CASCADE.

Previously the FK was created without cascade, causing an IntegrityError
when deleting users who have query history. This migration drops the old
constraint and recreates it with ON DELETE CASCADE so that deleting a user
automatically removes all their query logs.

Revision ID: 003
Revises: 002
Create Date: 2026-04-24
"""
from alembic import op

revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop the original FK (no cascade) and replace with one that cascades.
    op.drop_constraint('query_logs_user_id_fkey', 'query_logs', type_='foreignkey')
    op.create_foreign_key(
        'query_logs_user_id_fkey',
        'query_logs', 'users',
        ['user_id'], ['id'],
        ondelete='CASCADE',
    )


def downgrade() -> None:
    # Restore the original FK without cascade.
    op.drop_constraint('query_logs_user_id_fkey', 'query_logs', type_='foreignkey')
    op.create_foreign_key(
        'query_logs_user_id_fkey',
        'query_logs', 'users',
        ['user_id'], ['id'],
    )
