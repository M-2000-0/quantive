"""merge heads

Revision ID: 1fd54de1246e
Revises: 008_management, 72f492cf0553
Create Date: 2026-09-03 22:48:59.568487
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '1fd54de1246e'
down_revision: Union[str, None] = ('008_management', '72f492cf0553')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
