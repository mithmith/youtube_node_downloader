import logging
from multiprocessing import Queue

from app.config import settings
from app.service.telegram import TelegramBotService
from app.service.utils import load_channels_data
from app.service.yt_monitor import YTMonitorService

# Настройка уровня логирования SQLAlchemy
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.orm").setLevel(logging.WARNING)

# Удаляем все дополнительные обработчики, если они существуют
for handler in logging.getLogger("sqlalchemy.engine").handlers:
    logging.getLogger("sqlalchemy.engine").removeHandler(handler)


if __name__ == "__main__":
    # Общая очередь для передачи данных между сервисами
    news_queue = Queue()
    if settings.run_tg_bot_shorts_publish:
        shorts_queue = Queue()
    else:
        shorts_queue = None
    # Загружаем список каналов
    channels_list, channels_name = load_channels_data(settings.channels_list_path)

    # Инициализируем мониторинг YouTube
    monitor = YTMonitorService(
        channels_list[:10], channels_name, new_videos_queue=news_queue, shorts_videos_queue=shorts_queue
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
