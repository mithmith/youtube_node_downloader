import logging
from multiprocessing import Queue
import json

from loguru import logger

from app.config import settings
from app.db.data_table import Channel
from app.integrations.ytapi import YTApiClient
from app.integrations.ytdlp import YTChannelDownloader
from app.schema import ChannelAPIInfoSchema, ChannelInfoSchema
from app.service.telegram import TelegramBotService
from app.service.yt_monitor import YTMonitorService

# Настройка уровня логирования SQLAlchemy
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.orm").setLevel(logging.WARNING)
# Удаляем все дополнительные обработчики, если они существуют
for handler in logging.getLogger("sqlalchemy.engine").handlers:
    logging.getLogger("sqlalchemy.engine").removeHandler(handler)

# 1
# downloader = YTChannelDownloader("https://www.youtube.com/@BorisYulin")
# 1.1
# with open("yt-dlp_response.json", 'w', encoding='utf-8') as f:
#     json.dump(downloader._get_channel_data(channels_list["channels"][0]), fp=f, ensure_ascii=False, indent=4)
# 1.2
# ytdlp_channel_info: ChannelInfoSchema = downloader.get_channel_info()
# logger.debug(f"ytdlp_channel_info: {ytdlp_channel_info}")
# 1.2
# video_list, channel_id = downloader.get_video_list()
# new_videos, old_videos = downloader.filter_new_old(video_list, channel_id)

# 2
# downloader = YTApiClient()
# 2.1
# ytapi_channel_info: ChannelAPIInfoSchema = downloader.get_channel_info([ytdlp_channel_info.channel_id])[0]
# logger.debug(f"ytapi_channel_info: {ytapi_channel_info}")
# 2.2
# print(downloader.get_video_info(["QpwJEYGCngI"]))
# downloader.update_video_info(["QpwJEYGCngI"])
# downloader.update_missing_video_info()

# 3
# downloader = YTDownloader()
# for i in range(500):
#     logger.debug(f"Step №{i+1}")
#     downloader.update_video_formats()

def load_channels_list(file_path: str = "channels_list.json") -> list:
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
    queue = Queue()
    # Загружаем список каналов
    channels_list = load_channels_list()

    # 4
    # Инициализируем мониторинг YouTube
    monitor = YTMonitorService(channels_list=channels_list, new_videos_queue=queue)
    # channel_info: Channel = monitor._combine_channel_info(ytdlp_channel_info, ytapi_channel_info)
    # logger.debug(f"channel_info: {channel_info}")
    # new_videos = monitor.monitor_channels_for_newold_videos()
    # logger.debug(f"new_videos: {len(new_videos)}")

    # Запускаем процессы
    monitor_processes = monitor.run(monitor_new=True, monitor_history=False)
    tg_bot = TelegramBotService(
        bot_token=settings.tg_bot_token, group_id=settings.tg_group_id, queue=queue, users_ids=[settings.tg_admin_id]
    )
    bot_process = tg_bot.run()

    # Ожидание завершения
    bot_process.join()
    for process in monitor_processes:
        process.join()
