"""add session fields and drive links

Revision ID: e2b6a1d4c9f0
Revises: fd8dde07b42e
Create Date: 2026-03-06 12:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e2b6a1d4c9f0'
down_revision: Union[str, None] = 'fd8dde07b42e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('conversations', sa.Column('name', sa.String(), nullable=True))
    op.add_column('conversations', sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True))

    op.add_column('generated_assets', sa.Column('conversation_id', sa.String(), nullable=True))
    op.add_column('generated_assets', sa.Column('drive_id', sa.String(), nullable=True))
    op.add_column('generated_assets', sa.Column('drive_url', sa.String(), nullable=True))
    op.add_column('generated_assets', sa.Column('drive_direct_url', sa.String(), nullable=True))

    op.alter_column('generated_assets', 'job_id', existing_type=sa.String(), nullable=True)
    op.create_foreign_key(
        'fk_generated_assets_conversation_id',
        'generated_assets',
        'conversations',
        ['conversation_id'],
        ['id'],
    )


def downgrade() -> None:
    op.drop_constraint('fk_generated_assets_conversation_id', 'generated_assets', type_='foreignkey')
    op.alter_column('generated_assets', 'job_id', existing_type=sa.String(), nullable=False)

    op.drop_column('generated_assets', 'drive_direct_url')
    op.drop_column('generated_assets', 'drive_url')
    op.drop_column('generated_assets', 'drive_id')
    op.drop_column('generated_assets', 'conversation_id')

    op.drop_column('conversations', 'updated_at')
    op.drop_column('conversations', 'name')
