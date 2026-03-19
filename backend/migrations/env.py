from logging.config import fileConfig
from sqlalchemy import create_engine
from alembic import context
import os, sys
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.core.database import Base
from app.models import user, tryon, product  # noqa — register models

config = context.config

if config.config_file_name:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Get database URL from environment, convert asyncpg to psycopg2 for sync migrations
database_url = os.getenv("DATABASE_URL", "").replace("+asyncpg", "+psycopg2")

def run_migrations_offline():
    context.configure(url=database_url, target_metadata=target_metadata,
                       literal_binds=True, dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    connectable = create_engine(database_url)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
