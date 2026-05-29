from sqlalchemy import text
from sqlalchemy.orm import Session


SEQUENCE_TABLES = (
    "user",
    "classroom",
    "student",
    "content",
    "question",
    "test",
    "test_response",
)


def sync_table_id_sequence(db: Session, table_name: str) -> None:
    db.execute(
        text(
            f"""
            SELECT setval(
                pg_get_serial_sequence('"{{table_name}}"', 'id'),
                COALESCE((SELECT MAX(id) FROM "{{table_name}}"), 1),
                (SELECT MAX(id) IS NOT NULL FROM "{{table_name}}")
            )
            """.replace("{table_name}", table_name)
        )
    )


def sync_known_sequences(db: Session, table_names: tuple[str, ...] = SEQUENCE_TABLES) -> None:
    for table_name in table_names:
        sync_table_id_sequence(db, table_name)
