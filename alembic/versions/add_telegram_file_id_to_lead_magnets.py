"""add telegram_file_id to lead_magnets

Revision ID: add_telegram_file_id
Revises: 
Create Date: 2025-10-13

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_telegram_file_id'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Добавляем поле telegram_file_id в таблицу lead_magnets."""
    op.add_column('lead_magnets', sa.Column('telegram_file_id', sa.Text(), nullable=True))


def downgrade() -> None:
    """Удаляем поле telegram_file_id из таблицы lead_magnets."""
    op.drop_column('lead_magnets', 'telegram_file_id')

