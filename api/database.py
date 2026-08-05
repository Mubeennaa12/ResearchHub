import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config import settings
from api.models import Base

# Ensure the local data directory exists if SQLite is selected
if settings.database_url.startswith("sqlite"):
    # Extract path from database URL (e.g. "sqlite:///./data/sqlite.db" -> "./data/sqlite.db")
    db_path = settings.database_url.replace("sqlite:///", "")
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)

# Connect arguments for SQLite to allow multiple threads to access it
connect_args = {}
if settings.database_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Create all database tables."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """FastAPI Dependency for database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
