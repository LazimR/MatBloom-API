"""consolidate test library and application model

Revision ID: 20260323_0001
Revises:
Create Date: 2026-03-23 00:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260323_0001"
down_revision: Union[str, None] = "20260401_0000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _add_column_if_missing(table_name: str, column: sa.Column) -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = {item["name"] for item in inspector.get_columns(table_name)}
    if column.name not in existing_columns:
        op.add_column(table_name, column)


def _drop_column_if_exists(table_name: str, column_name: str) -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = {item["name"] for item in inspector.get_columns(table_name)}
    if column_name in existing_columns:
        op.drop_column(table_name, column_name)


def _create_fk_if_missing(
    table_name: str,
    constraint_name: str,
    local_columns: list[str],
    referred_table: str,
    remote_columns: list[str],
) -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table(table_name) or not inspector.has_table(referred_table):
        return

    foreign_keys = inspector.get_foreign_keys(table_name)
    for fk in foreign_keys:
        if (
            fk.get("referred_table") == referred_table
            and fk.get("constrained_columns") == local_columns
            and fk.get("referred_columns") == remote_columns
        ):
            return

    op.create_foreign_key(
        constraint_name,
        table_name,
        referred_table,
        local_columns,
        remote_columns,
    )


def _drop_fk_if_exists(table_name: str, constraint_name: str) -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    fk_names = {fk["name"] for fk in inspector.get_foreign_keys(table_name)}
    if constraint_name in fk_names:
        op.drop_constraint(constraint_name, table_name, type_="foreignkey")


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("test"):
        return

    _add_column_if_missing(
        "test",
        sa.Column("theme", sa.String(), nullable=False, server_default=sa.text("'Geral'")),
    )
    _add_column_if_missing("test", sa.Column("application_date", sa.Date(), nullable=True))
    _add_column_if_missing("test", sa.Column("created_by_user_id", sa.Integer(), nullable=True))
    _add_column_if_missing("test", sa.Column("applied_by_user_id", sa.Integer(), nullable=True))
    _add_column_if_missing("test", sa.Column("classroom_id", sa.Integer(), nullable=True))
    _add_column_if_missing("test", sa.Column("source_test_id", sa.Integer(), nullable=True))
    _add_column_if_missing(
        "test",
        sa.Column("kind", sa.String(), nullable=False, server_default=sa.text("'template'")),
    )
    _add_column_if_missing(
        "test",
        sa.Column("visibility", sa.String(), nullable=False, server_default=sa.text("'private'")),
    )
    _add_column_if_missing(
        "test",
        sa.Column("target_type", sa.String(), nullable=False, server_default=sa.text("'individual'")),
    )
    _add_column_if_missing(
        "test",
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
    )

    _create_fk_if_missing(
        "test",
        "fk_test_created_by_user_id_user",
        ["created_by_user_id"],
        "user",
        ["id"],
    )
    _create_fk_if_missing(
        "test",
        "fk_test_applied_by_user_id_user",
        ["applied_by_user_id"],
        "user",
        ["id"],
    )
    _create_fk_if_missing(
        "test",
        "fk_test_classroom_id_classroom",
        ["classroom_id"],
        "classroom",
        ["id"],
    )
    _create_fk_if_missing(
        "test",
        "fk_test_source_test_id_test",
        ["source_test_id"],
        "test",
        ["id"],
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("test"):
        return

    _drop_fk_if_exists("test", "fk_test_source_test_id_test")
    _drop_fk_if_exists("test", "fk_test_classroom_id_classroom")
    _drop_fk_if_exists("test", "fk_test_applied_by_user_id_user")
    _drop_fk_if_exists("test", "fk_test_created_by_user_id_user")

    _drop_column_if_exists("test", "created_at")
    _drop_column_if_exists("test", "target_type")
    _drop_column_if_exists("test", "visibility")
    _drop_column_if_exists("test", "kind")
    _drop_column_if_exists("test", "source_test_id")
    _drop_column_if_exists("test", "classroom_id")
    _drop_column_if_exists("test", "applied_by_user_id")
    _drop_column_if_exists("test", "created_by_user_id")
    _drop_column_if_exists("test", "application_date")
    _drop_column_if_exists("test", "theme")
