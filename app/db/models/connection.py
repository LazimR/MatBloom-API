import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

load_dotenv()


def get_database_url() -> str:
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return database_url

    db_user = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASSWORD")
    db_host = os.getenv("DB_HOST")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME")

    required_values = {
        "DB_USER": db_user,
        "DB_PASSWORD": db_password,
        "DB_HOST": db_host,
        "DB_NAME": db_name,
    }
    missing_values = [name for name, value in required_values.items() if not value]
    if missing_values:
        missing = ", ".join(missing_values)
        raise RuntimeError(
            "Database configuration is incomplete. "
            f"Set DATABASE_URL or define: {missing}."
        )

    return f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"


DB_URL = get_database_url()
engine = create_engine(DB_URL, pool_pre_ping=True, pool_size=7)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
