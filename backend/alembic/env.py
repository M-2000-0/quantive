from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import os, sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.database import Base
from app.models import *  # noqa: ensure all models are imported
from app.models.password_reset import *  # noqa: ensure auth security models imported
from app.models.extended import *  # noqa: ensure extended models imported
from app.models.portfolio_access import *  # noqa: ensure portfolio access models
from app.models.social import *  # noqa: ensure social models
from app.models.integrations import *  # noqa: ensure integration models

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Use app config for database URL if available
try:
    from app.config import get_settings
    settings = get_settings()
    config.set_main_option('sqlalchemy.url', settings.DATABASE_URL)
except Exception:
    pass

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True, dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(config.get_section(config.config_ini_section, {}), prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
