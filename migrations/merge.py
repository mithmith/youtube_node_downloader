import logging
from sqlalchemy import create_engine, Table, MetaData
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects.postgresql import insert
from datetime import datetime
from tqdm import tqdm

from app.config import settings

# Настройки логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Настройки соединения
DB_CONFIGS = {
    "db1": {
        "host": settings.db_host,
        "port": settings.db_port,
        "database": settings.db_name,
        "user": settings.db_username,
        "password": settings.db_password,
    },
    "db2": {
        "host": "ip2",
        "port": "port2",
        "database": "db_name2",
        "user": "db_user2",
        "password": "db_pass2"
    }
}

SCHEMA = settings.db_schema

# Функция создания движка БД
def get_engine(config):
    """Создает подключение к базе данных."""
    try:
        engine = create_engine(
            f"postgresql://{config['user']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}"
        )
        logger.info(f"Успешное подключение к {config['database']} на {config['host']}")
        return engine
    except Exception as e:
        logger.error(f"Ошибка подключения к {config['database']} на {config['host']}: {e}")
        raise

# Подключение к БД
engines = {db: get_engine(DB_CONFIGS[db]) for db in DB_CONFIGS}
sessions = {db: sessionmaker(bind=engines[db])() for db in DB_CONFIGS}

# Метаданные и таблицы
metadata = MetaData(schema=SCHEMA)
try:
    metadata.reflect(bind=engines["db1"])  # Загружаем схему из первой БД
    logger.info("Метаданные успешно загружены.")
except Exception as e:
    logger.error(f"Ошибка загрузки метаданных: {e}")
    raise

def merge_table(table_name, timestamp_column=None):
    """Синхронизирует таблицы из второй базы в первую, обновляя по временным меткам."""
    try:
        logger.info(f"Объединение таблицы: {table_name}")
        table = Table(table_name, metadata, autoload_with=engines["db1"])
        
        data_db1 = sessions["db1"].execute(table.select()).fetchall()
        data_db2 = sessions["db2"].execute(table.select()).fetchall()
        
        merged_data = {}
        for row in data_db1 + data_db2:
            row_dict = dict(row)
            key = row_dict[table.primary_key.columns.keys()[0]]
            
            if key in merged_data:
                if timestamp_column and row_dict[timestamp_column] > merged_data[key][timestamp_column]:
                    merged_data[key] = row_dict
            else:
                merged_data[key] = row_dict
        
        # Вставка данных с конфликтами
        with engines["db1"].begin() as conn:
            for row in tqdm(merged_data.values(), desc=f"Слияние {table_name}"):
                insert_stmt = insert(table).values(row)
                if timestamp_column:
                    update_stmt = insert_stmt.on_conflict_do_update(
                        index_elements=[table.primary_key.columns.keys()[0]],
                        set_={timestamp_column: row[timestamp_column]}
                    )
                else:
                    update_stmt = insert_stmt.on_conflict_do_nothing()
                conn.execute(update_stmt)
        logger.info(f"Таблица {table_name} успешно объединена.")
    except Exception as e:
        logger.error(f"Ошибка при объединении таблицы {table_name}: {e}")
        raise

def merge_databases():
    """Запускает процесс объединения всех таблиц баз данных."""
    try:
        logger.info("Начало объединения баз данных")
        tables_with_timestamps = [
            ("channels", "last_update"),
            ("channel_history", "recorded_at"),
            ("videos", "last_update"),
            ("video_history", "recorded_at"),
        ]
        tables_without_timestamps = [
            "tags", "videotag", "thumbnails", "video_formats"
        ]
        
        for table, timestamp in tqdm(tables_with_timestamps, desc="Обновление с временными метками"):
            merge_table(table, timestamp)
        
        for table in tqdm(tables_without_timestamps, desc="Обновление без временных меток"):
            merge_table(table)
        
        logger.info("Объединение баз данных завершено.")
    except Exception as e:
        logger.error(f"Ошибка объединения баз данных: {e}")
        raise

if __name__ == "__main__":
    merge_databases()

