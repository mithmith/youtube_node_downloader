import json
import logging
from multiprocessing import Queue

from loguru import logger

from app.config import settings
from app.service.telegram import TelegramBotService
from app.service.yt_monitor import YTMonitorService

# Настройка уровня логирования SQLAlchemy
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.orm").setLevel(logging.WARNING)

# Удаляем все дополнительные обработчики, если они существуют
for handler in logging.getLogger("sqlalchemy.engine").handlers:
    logging.getLogger("sqlalchemy.engine").removeHandler(handler)


def load_channels_list(file_path: str = "channels_list.json") -> list[str]:
    """
    Загружает список каналов из JSON файла.

    :param file_path: Путь к JSON файлу.
    :return: Список каналов или пустой список в случае ошибки.
    """
    try:
        logger.debug(f"Channels list loading from {file_path}")
        with open(file_path, encoding="utf8") as f:
            data = json.load(f)
            channels = data.get("channels", [])
            logger.debug(f"Loaded {len(channels)} channels")
            return channels
    except FileNotFoundError:
        logger.error(f"Файл {file_path} не найден")
    except json.JSONDecodeError as e:
        logger.error(f"Ошибка декодирования JSON: {e}")
    except Exception as e:
        logger.error(f"Неизвестная ошибка при загрузке списка каналов: {e}")
    return []


if __name__ == "__main__":
    # Общая очередь для передачи данных между сервисами
    news_queue = Queue()
    if settings.run_tg_bot_shorts_publish:
        shorts_queue = Queue()
    else:
        shorts_queue = None
    # Загружаем список каналов
    channels_list = load_channels_list()

    # Инициализируем мониторинг YouTube
    monitor = YTMonitorService(
        channels_list=channels_list[-1], new_videos_queue=news_queue, shorts_publish=settings.run_tg_bot_shorts_publish
    )

    # Запускаем процессы
    monitor_processes = monitor.run(settings.monitor_new, settings.monitor_history, settings.monitor_video_formats)
    logger.debug(f"TG bot started: {settings.run_tg_bot}")
    if settings.run_tg_bot:
        tg_bot = TelegramBotService(
            bot_token=settings.tg_bot_token,
            group_id=settings.tg_group_id,
            msg_queue=news_queue,
            shorts_queue=shorts_queue,
        )
        bot_process = tg_bot.run()
        bot_process.join()

    for process in monitor_processes:
        process.join()
