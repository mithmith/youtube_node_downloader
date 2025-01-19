from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
import psycopg2

from alembic import context
from app.config import settings
from app.db.data_table import Base

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.

def create_database_if_not_exists():
    # Подключаемся к PostgreSQL без указания базы данных (это подключение к шаблонной базе)
    conn = psycopg2.connect(
        dbname="postgres",  # подключаемся к базе данных по умолчанию
        user=settings.db_username,
        password=settings.db_password,
        host=settings.db_host,
        port=settings.db_port
    )
    conn.autocommit = True  # для создания базы данных в текущем сеансе
    cursor = conn.cursor()

    # Проверяем, существует ли база данных
    cursor.execute(f"SELECT 1 FROM pg_database WHERE datname = '{settings.db_name}';")
    if not cursor.fetchone():
        # Создаём базу данных, если её нет
        cursor.execute(f"CREATE DATABASE {settings.db_name};")
        print(f"База данных {settings.db_name} была успешно создана.")
    else:
        print(f"База данных {settings.db_name} уже существует.")
    
    # Закрываем соединение
    cursor.close()
    conn.close()

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
        version_table_schema=settings.db_schema,
        literal_binds=True,
        version_table="alembic_version",
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
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


create_database_if_not_exists()
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
