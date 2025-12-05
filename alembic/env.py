from logging.config import fileConfig

import asyncio

# --- NEW: Import create_async_engine for async driver support ---
from sqlalchemy.ext.asyncio import create_async_engine
# --- END NEW ---

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Import all models here so Alembic can detect them
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

# --- Using your confirmed working import path ---
from app.core.config import settings
# --- END NEW ---

from app.database import Base
# Import all models so Alembic can detect them
from app.models import * # noqa


# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.
    ...
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


# --- MODIFIED: Changed to an async function ---
async def run_migrations_online() -> None:
    """Run migrations in 'online' mode (Async implementation).
    """
    
    # 1. Get the raw URL string from your settings object.
    connectable_url = settings.DATABASE_URL
    
    # 2. MODIFIED: Create the AsyncEngine directly.
    connectable = create_async_engine(
        connectable_url,
        poolclass=pool.NullPool,
    )

    # --- NEW INNER FUNCTION: Defines the entire synchronous block ---
    def do_run_migrations(connection):
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()
    # --- END NEW INNER FUNCTION ---
    
    # 3. MODIFIED: Use the asynchronous connection context manager.
    async with connectable.connect() as connection:
        
        # 4. MODIFIED: Run the entire Alembic logic inside connection.run_sync()
        # This ensures all synchronous database access by Alembic is properly wrapped.
        await connection.run_sync(do_run_migrations)


if context.is_offline_mode():
    run_migrations_offline()
else:
    # --- MODIFIED: Execute the async function synchronously ---
    asyncio.run(run_migrations_online())
    # --- END MODIFIED ---
