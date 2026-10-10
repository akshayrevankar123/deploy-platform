"""Database connection.

By default we use SQLite (a single file, zero setup) so you can start
immediately. Later, set DATABASE_URL to a PostgreSQL URL and nothing else changes.
"""
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")

# SQLite needs this flag because FastAPI uses several threads.
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False)


class Base(DeclarativeBase):
    pass


def get_db():
    """Gives each request its own database session and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
