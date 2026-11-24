"""Persist question order for newly created exams.

Revision ID: 20261121_0003
Revises: 20260401_0002
"""
from alembic import op
import sqlalchemy as sa

revision = "20261121_0003"
down_revision = "20260401_0002"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("test", sa.Column("question_order_confirmed", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("test_question", sa.Column("position", sa.Integer(), nullable=True))
    op.create_unique_constraint("uq_test_question_position", "test_question", ["test_id", "position"])
    op.create_check_constraint("ck_test_question_position_positive", "test_question", "position IS NULL OR position > 0")


def downgrade():
    op.drop_constraint("ck_test_question_position_positive", "test_question", type_="check")
    op.drop_constraint("uq_test_question_position", "test_question", type_="unique")
    op.drop_column("test_question", "position")
    op.drop_column("test", "question_order_confirmed")
