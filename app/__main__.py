import json
import logging
import re
from multiprocessing import Queue

from app.config import logger, settings
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
    Загружает список YouTube-каналов из txt или JSON файла, проверяет валидность, корректирует и удаляет дубликаты.
    """
    patterns = {
        "channel": re.compile(r"^https://www\.youtube\.com/channel/([a-zA-Z0-9_-]+)(/videos)?$"),
        "handle": re.compile(r"^https://www\.youtube\.com/@([a-zA-Z0-9_.-]+)(/videos)?$"),
        "custom": re.compile(r"^https://www\.youtube\.com/c/([a-zA-Z0-9_-]+)(/videos)?$"),
    }

    valid_urls = set()

    try:
        if file_path.endswith(".json"):
            with open(file_path, encoding="utf8") as f:
                data = json.load(f)
                channels = set(data.get("channels", []))
        elif file_path.endswith(".txt"):
            with open(file_path, "r", encoding="utf-8") as file:
                channels = {line.strip() for line in file if line.strip()}
        else:
            raise ValueError("Неподдерживаемый формат файла. Используйте .json или .txt")

        for url in channels:
            for _, pattern in patterns.items():
                match = pattern.match(url)
                if match:
                    base_url = match.group(0).split("/videos")[0]
                    valid_urls.add(base_url)
                    break
            else:
                if url.startswith("https://www.youtube.com/channel/") and "/videos" not in url:
                    valid_urls.add(url + "/videos")
                elif url.startswith("https://www.youtube.com/@") and "/videos" in url:
                    valid_urls.add(url.replace("/videos", ""))
                else:
                    logger.warning(f"Некорректный URL: {url}")
    except FileNotFoundError:
        logger.error(f"Файл {file_path} не найден")
    except json.JSONDecodeError as e:
        logger.error(f"Ошибка декодирования JSON: {e}")
    except Exception as e:
        logger.error(f"Неизвестная ошибка: {e}")
    logger.debug(f"Всего загружено {len(valid_urls)} каналов")
    return sorted(valid_urls)


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
        channels_list=channels_list, new_videos_queue=news_queue, shorts_videos_queue=shorts_queue
    )

    # Запускаем процессы
    # logger.debug(f"Current Settings: {settings.model_dump()}")
    monitor_processes = monitor.run(settings.monitor_new, settings.monitor_history, settings.monitor_video_formats)
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
