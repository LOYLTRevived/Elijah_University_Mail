import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# -------------------------------------------------------------
# 1. NEW IMPORTS & PATH SETUP
# -------------------------------------------------------------
# Add the current directory to the path so we can import 'app' and 'config'
sys.path.append(os.getcwd())

# Import your SQLAlchemy instance and models
from app import db # We only need 'db' to get the metadata
# Note: You don't technically need Entry and Media here, but importing db 
# implicitly loads the models defined on it.

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# -------------------------------------------------------------
# 2. SET TARGET METADATA & CONNECTION URL
# -------------------------------------------------------------

# Set target_metadata to the metadata associated with your SQLAlchemy instance.
# This allows Alembic to see your current model structure (Entry and Media).
target_metadata = db.metadata

# Use your provided absolute path for the migration connection
DATABASE_ABSOLUTE_PATH = r"F:/Elijah_University_Mail/database.db" # Using \ instead of / for robustness on Windows
CONNECTABLE_URL = 'sqlite:///' + DATABASE_ABSOLUTE_PATH


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode. (Unchanged)"""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode."""
    
    # 1. Get configuration and set the URL to the absolute path
    configuration = config.get_section(config.config_ini_section)
    # CRITICAL: Use the absolute URL here to ensure connection is found
    configuration['sqlalchemy.url'] = CONNECTABLE_URL 
    
    # 2. Create the engine from the configuration
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    # 3. Use the engine to establish a connection and configure the context
    # The 'with' statement ensures the connection is closed after the operation
    with connectable.connect() as connection:
        
        # Configure the context with the *active connection object*
        context.configure(
            connection=connection, # 🚨 FIX: Pass the connection object instead of just the URL
            target_metadata=target_metadata,
            render_as_batch=True,
            dialect_opts={"paramstyle": "named"},
        )

        # Run migrations within the transaction on that connection
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()