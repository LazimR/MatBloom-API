"""Record whether an application counts toward overall averages.

Revision ID: 20261122_0004
Revises: 20261121_0003
"""
from alembic import op
import sqlalchemy as sa

revision = "20261122_0004"
down_revision = "20261121_0003"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("test", sa.Column("counts_toward_average", sa.Boolean(), nullable=False, server_default=sa.true()))


def downgrade():
    op.drop_column("test", "counts_toward_average")
