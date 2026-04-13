import uuid
from logging.config import fileConfig

from alembic import context
from alembic.script import ScriptDirectory
from psycopg2 import DatabaseError
from sqlalchemy import create_engine

from api.database.models import BaseModel
from core.config import settings

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def get_sync_url() -> str:
    url = settings.TEST_DB_URL if settings.TESTING else settings.PROD_DB_URL
    return url.replace("postgresql+asyncpg", "postgresql+psycopg2")


config.set_main_option("sqlalchemy.url", get_sync_url())


def process_revision_directives(context, revision, directives):
    migration_script = directives[0]
    head_revision = ScriptDirectory.from_config(context.config).get_current_head()

    if head_revision is None:
        new_rev_id = 1
    else:
        last_rev_id = int(head_revision[:4].lstrip("0"))
        new_rev_id = last_rev_id + 1
    migration_script.rev_id = f"{new_rev_id:04}_{uuid.uuid4().hex[-12:]}"


target_metadata = BaseModel.metadata


def run_migrations_offline() -> None:
    if settings.TESTING:
        raise DatabaseError(
            "Running testing migrations offline currently not permitted."
        )

    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        process_revision_directives=process_revision_directives,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(get_sync_url())

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            process_revision_directives=process_revision_directives,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
