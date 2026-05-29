"""create baseline schema

Revision ID: 20260401_0000
Revises:
Create Date: 2026-04-01 00:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "20260401_0000"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "classroom",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("school_year", sa.Integer(), nullable=False),
        sa.Column("grade_level", sa.String(), nullable=False),
        sa.Column("shift", sa.String(), nullable=False, server_default=sa.text("'manha'")),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "content",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    op.create_table(
        "question",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("enunciation", sa.String(), nullable=False),
        sa.Column("itens", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column("correct_item", sa.Integer(), nullable=True),
        sa.Column("level", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "user",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("username", sa.String(), nullable=False),
        sa.Column("password", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False, server_default=sa.text("'professor'")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("username"),
    )

    op.create_table(
        "question_content",
        sa.Column("question_id", sa.Integer(), nullable=False),
        sa.Column("content_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["content_id"], ["content.id"]),
        sa.ForeignKeyConstraint(["question_id"], ["question.id"]),
        sa.PrimaryKeyConstraint("question_id", "content_id"),
    )

    op.create_table(
        "question_dependency",
        sa.Column("question_id", sa.Integer(), nullable=False),
        sa.Column("dependency_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["dependency_id"], ["question.id"]),
        sa.ForeignKeyConstraint(["question_id"], ["question.id"]),
        sa.PrimaryKeyConstraint("question_id", "dependency_id"),
    )

    op.create_table(
        "student",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("registration", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("classroom_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["classroom_id"], ["classroom.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("registration"),
    )

    op.create_table(
        "test",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("theme", sa.String(), nullable=False),
        sa.Column("application_date", sa.Date(), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column("applied_by_user_id", sa.Integer(), nullable=True),
        sa.Column("classroom_id", sa.Integer(), nullable=True),
        sa.Column("source_test_id", sa.Integer(), nullable=True),
        sa.Column("kind", sa.String(), nullable=False, server_default=sa.text("'template'")),
        sa.Column("visibility", sa.String(), nullable=False, server_default=sa.text("'private'")),
        sa.Column("target_type", sa.String(), nullable=False, server_default=sa.text("'individual'")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["applied_by_user_id"], ["user.id"]),
        sa.ForeignKeyConstraint(["classroom_id"], ["classroom.id"]),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["user.id"]),
        sa.ForeignKeyConstraint(["source_test_id"], ["test.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "user_classroom",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("classroom_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["classroom_id"], ["classroom.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("user_id", "classroom_id"),
    )

    op.create_table(
        "test_question",
        sa.Column("test_id", sa.Integer(), nullable=False),
        sa.Column("question_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["question_id"], ["question.id"]),
        sa.ForeignKeyConstraint(["test_id"], ["test.id"]),
        sa.PrimaryKeyConstraint("test_id", "question_id"),
    )

    op.create_table(
        "test_response",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("test_id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("responses", postgresql.ARRAY(sa.Integer()), nullable=False),
        sa.Column("wrong_questions", postgresql.ARRAY(sa.Integer()), nullable=True),
        sa.Column("attempt_date", sa.Date(), nullable=False, server_default=sa.text("CURRENT_DATE")),
        sa.ForeignKeyConstraint(["student_id"], ["student.id"]),
        sa.ForeignKeyConstraint(["test_id"], ["test.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("test_response")
    op.drop_table("test_question")
    op.drop_table("user_classroom")
    op.drop_table("test")
    op.drop_table("student")
    op.drop_table("question_dependency")
    op.drop_table("question_content")
    op.drop_table("user")
    op.drop_table("question")
    op.drop_table("content")
    op.drop_table("classroom")
