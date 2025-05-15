from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager

DB_URL= "postgresql://postgres:postgres@matbloom-db:5432/matbloom"
engine = create_engine(DB_URL, pool_pre_ping=True, pool_size=7)
SessionLocal = sessionmaker(autocommit=False,autoflush=False,bind=engine)

# database.py
def get_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
