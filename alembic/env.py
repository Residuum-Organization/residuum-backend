import os
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config
from sqlalchemy import pool
from dotenv import load_dotenv

from alembic import context

# Garante que o pacote 'app' seja importável quando rodando alembic da raiz
sys.path.append(str(Path(__file__).resolve().parents[1]))

# Carrega variáveis do .env (DATABASE_URL)
load_dotenv()

# Importa Base e todos os modelos para que o autogenerate enxergue as tabelas
from app.database import Base  # noqa: E402
import app.models.usuario  # noqa: F401, E402
import app.models.endereco  # noqa: F401, E402
import app.models.descarte # noqa: F401, E402
import app.models.estoque # noqa: F401, E402
import app.models.pontuacao # noqa: F401, E402
import app.models.ponto_coleta # noqa: F401, E402
import app.models.solicitacao_ponto_coleta # noqa: F401, E402
import app.models.qrcode_token # noqa: F401, E402
import app.models.inventario_usuario # noqa: F401, E402
import app.models.notificacao # noqa: F401, E402
import app.models.resgate_pontuacao # noqa: F401, E402
import app.models.sorteio # noqa: F401, E402
import app.models.voucher # noqa: F401, E402
import app.models.resgate_voucher # noqa: F401, E402
import app.models.bilhete_sorteio # noqa: F401, E402
import app.models.campanha # noqa: F401, E402
import app.models.audit_log # noqa: F401, E402
import app.models.agenda # noqa: F401, E402
# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Sobrescreve a URL do banco com a do .env
database_url = os.getenv("DATABASE_URL")
if database_url:
    config.set_main_option("sqlalchemy.url", database_url)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata alvo para autogenerate
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

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


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
