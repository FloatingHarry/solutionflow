from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import settings
from app.db.base import Base
from app.modules.accounts import models  # noqa: F401
from app.modules.agent import models as agent_models  # noqa: F401
from app.modules.business_case import models as business_case_models  # noqa: F401
from app.modules.deployment import models as deployment_models  # noqa: F401
from app.modules.discovery import models as discovery_models  # noqa: F401
from app.modules.evaluation import models as evaluation_models  # noqa: F401
from app.modules.poc import models as poc_models  # noqa: F401
from app.modules.research import models as research_models  # noqa: F401
from app.modules.solutions import models as solution_models  # noqa: F401

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
