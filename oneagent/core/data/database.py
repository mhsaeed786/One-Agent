"""
Database - SQLModel engine and session management
"""

import os
from typing import Optional

from sqlmodel import SQLModel, create_engine, Session

from ..logging import get_logger

logger = get_logger("data.database")

_engine = None


def get_engine(db_path: Optional[str] = None):
    """Get or create the database engine."""
    global _engine
    if _engine is None:
        db_url = db_path or os.getenv(
            "ONEAGENT_DB_URL", f"sqlite:///{os.getcwd()}/oneagent.db"
        )
        _engine = create_engine(db_url, echo=False)
        logger.info(f"Database engine created: {db_url}")
    return _engine


def get_session():
    """Get a database session."""
    engine = get_engine()
    return Session(engine)


def init_db(db_path: Optional[str] = None):
    """Initialize database and create tables."""
    engine = get_engine(db_path)
    SQLModel.metadata.create_all(engine)
    logger.info("Database tables created")
