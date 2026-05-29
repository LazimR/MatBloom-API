"""add individual applications and template versioning

Revision ID: 20260401_0002
Revises: 20260323_0001
Create Date: 2026-04-01 00:30:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260401_0002"
down_revision: Union[str, None] = "20260323_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return column_name in {item["name"] for item in inspector.get_columns(table_name)}


def _has_fk(table_name: str, local_columns: list[str], referred_table: str, remote_columns: list[str]) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    for fk in inspector.get_foreign_keys(table_name):
        if (
            fk.get("constrained_columns") == local_columns
            and fk.get("referred_table") == referred_table
            and fk.get("referred_columns") == remote_columns
        ):
            return True
    return False


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("test"):
        return

    if not _has_column("test", "student_id"):
        op.add_column("test", sa.Column("student_id", sa.Integer(), nullable=True))
    if not _has_column("test", "template_group_id"):
        op.add_column("test", sa.Column("template_group_id", sa.Integer(), nullable=True))
    if not _has_column("test", "version_number"):
        op.add_column(
            "test",
            sa.Column("version_number", sa.Integer(), nullable=False, server_default=sa.text("1")),
        )

    if not _has_fk("test", ["student_id"], "student", ["id"]):
        op.create_foreign_key("fk_test_student_id_student", "test", "student", ["student_id"], ["id"])
    if not _has_fk("test", ["template_group_id"], "test", ["id"]):
        op.create_foreign_key(
            "fk_test_template_group_id_test",
            "test",
            "test",
            ["template_group_id"],
            ["id"],
        )

    op.execute("UPDATE test SET template_group_id = COALESCE(template_group_id, id)")
    op.execute("UPDATE test SET version_number = COALESCE(version_number, 1)")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("test"):
        return

    fk_names = {fk["name"] for fk in inspector.get_foreign_keys("test")}
    if "fk_test_template_group_id_test" in fk_names:
        op.drop_constraint("fk_test_template_group_id_test", "test", type_="foreignkey")
    if "fk_test_student_id_student" in fk_names:
        op.drop_constraint("fk_test_student_id_student", "test", type_="foreignkey")

    if _has_column("test", "version_number"):
        op.drop_column("test", "version_number")
    if _has_column("test", "template_group_id"):
        op.drop_column("test", "template_group_id")
    if _has_column("test", "student_id"):
        op.drop_column("test", "student_id")
