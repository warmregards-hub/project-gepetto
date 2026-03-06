"""add session id to cost entries

Revision ID: f1d2c3b4a5f6
Revises: e2b6a1d4c9f0
Create Date: 2026-03-06 13:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f1d2c3b4a5f6'
down_revision: Union[str, None] = 'e2b6a1d4c9f0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('cost_entries', sa.Column('session_id', sa.String(), nullable=True))
    op.create_foreign_key(
        'fk_cost_entries_session_id',
        'cost_entries',
        'conversations',
        ['session_id'],
        ['id'],
    )


def downgrade() -> None:
    op.drop_constraint('fk_cost_entries_session_id', 'cost_entries', type_='foreignkey')
    op.drop_column('cost_entries', 'session_id')
