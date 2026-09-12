"""Separate database for Quantive Personal.

Why a second file: the enterprise wants one app + shared billing/auth,
but Personal user data must never mix with Quantive sovereign/institutional data.
"""
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import get_settings

settings = get_settings()


def _personal_url() -> str:
    # Explicit setting wins; otherwise derive sibling file next to DATABASE_URL.
    url = getattr(settings, "PERSONAL_DATABASE_URL", "") or ""
    if url:
        return url
    main = settings.DATABASE_URL or "sqlite:///./quantive.db"
    if main.endswith("quantive.db"):
        return main.replace("quantive.db", "quantive_personal.db")
    if "sqlite" in main:
        return "sqlite:///./quantive_personal.db"
    # Postgres deployments: same server, separate database name.
    return main.replace("/quantive", "/quantive_personal")


PERSONAL_DATABASE_URL = _personal_url()

personal_engine = create_engine(
    PERSONAL_DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in PERSONAL_DATABASE_URL else {},
    pool_pre_ping=True,
    pool_recycle=3600,
    pool_timeout=30,
)


@event.listens_for(personal_engine, "connect")
def _personal_connect(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    try:
        if "sqlite" in PERSONAL_DATABASE_URL:
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
    finally:
        cursor.close()


PersonalSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=personal_engine)


class PersonalBase(DeclarativeBase):
    pass


def get_personal_db():
    """Yield a Personal-DB session. Always scoped by user_id in queries."""
    db = PersonalSessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
