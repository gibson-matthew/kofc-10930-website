import asyncio
from logging.config import fileConfig

from alembic import context
from backend.app.models import prayer_requests
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.config import settings
from app.db.session import engine

# Import all models so Alembic can autogenerate migrations
from app.models import (
    user, role, news, recognition, memoriam, links, events,
    officers, directors, programs, committees, newsletters, photos, market, jobs, degree_schedule,
    documents, voting, audit_log, assemblies
)

config = context.config

# Logging
if config.config_file_name:
    fileConfig(config.config_file_name)

# Collect all metadata
target_metadata = [
    user.Base.metadata,
    role.Base.metadata,
    news.Base.metadata,
    recognition.Base.metadata,
    memoriam.Base.metadata,
    links.Base.metadata,
    events.Base.metadata,
    officers.Base.metadata,
    directors.Base.metadata,
    programs.Base.metadata,
    committees.Base.metadata,
    prayer_requests.Base.metadata,
    newsletters.Base.metadata,
    photos.Base.metadata,
    market.Base.metadata,
    jobs.Base.metadata,
    degree_schedule.Base.metadata,
    documents.Base.metadata,
    voting.Base.metadata,
    audit_log.Base.metadata,
    assemblies.Base.metadata,
]


def run_migrations_offline():
    """Run migrations in offline mode."""
    context.configure(
        url=settings.DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online():
    """Run migrations in online mode."""
    connectable: AsyncEngine = engine

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)


def do_run_migrations(connection: Connection):
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
