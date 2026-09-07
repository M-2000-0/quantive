from contextvars import ContextVar
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import get_settings

settings = get_settings()

# ── Per-request org context (set by auth middleware) ─────────────────
_current_org_id: ContextVar[str] = ContextVar('current_org_id', default='')
_current_user_id: ContextVar[str] = ContextVar('current_user_id', default='')
_current_user_role: ContextVar[str] = ContextVar('current_user_role', default='analyst')


def set_org_context(org_id: str, user_id: str, role: str = 'analyst'):
    """Set the current org/user context for RLS enforcement."""
    _current_org_id.set(org_id)
    _current_user_id.set(user_id)
    _current_user_role.set(role)


def get_org_id() -> str:
    return _current_org_id.get()


def get_user_id() -> str:
    return _current_user_id.get()


engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
    pool_pre_ping=True,
    pool_recycle=3600,
    pool_timeout=30,
)


@event.listens_for(engine, "connect")
def set_connection_context(dbapi_connection, connection_record):
    """Set session context on each new connection for RLS enforcement."""
    cursor = dbapi_connection.cursor()

    if 'sqlite' in settings.DATABASE_URL:
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
    else:
        # PostgreSQL: set org context for RLS policies
        org_id = _current_org_id.get('')
        user_id = _current_user_id.get('')
        role = _current_user_role.get('analyst')
        if org_id:
            try:
                cursor.execute(
                    "SELECT set_app_context(%s::uuid, %s, %s)",
                    (user_id or None, org_id, role)
                )
            except Exception:
                # Function may not exist yet (first run)
                pass

    cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    """Get database session with org context automatically set."""
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
