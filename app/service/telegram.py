import time
from multiprocessing import Process, Queue
from queue import Empty

from loguru import logger
from telegram import Bot

from app.schema import NewVideoSchema


class TelegramBotService:
    """Класс для публикации сообщений в Telegram."""

    def __init__(self, bot_token: str, group_id: str, queue: Queue, delay: int = 10):
        self._bot_token = bot_token
        self._group_id = group_id
        self._queue = queue
        self._delay = delay

    def run(self):
        """Запускает поток для публикации сообщений из очереди."""
        process = Process(target=self._publish_messages)
        process.start()
        return process

    async def _publish_messages(self):
        """Публикация сообщений из очереди каждые N секунд."""
        bot = Bot(token=self._bot_token)
        logger.info("Bot is running...")

        while True:
            try:
                # Получаем сообщение из очереди
                video: NewVideoSchema = self._queue.get(timeout=self._delay)  # Ждём сообщение
                logger.debug(f"video={video}")

                message = self._format_telegram_message(
                    video.channel_name, video.channel_url, video.video_title, video.video_url
                )
                await bot.send_message(
                    chat_id=self._group_id,
                    text=message,
                    parse_mode="Markdown",
                )

                # Задержка между отправками сообщений
                time.sleep(self._delay)
            except Empty:
                # Если очередь пуста после таймаута, ничего не делаем и продолжаем ждать
                continue
            except Exception as e:
                logger.error(f"Ошибка при отправке сообщения: {e}")

    def _format_telegram_message(self, channel_name, channel_url, video_title, video_url):
        """Форматирование сообщения в Markdown формате."""
        return f'**[{video_title}]({video_url})**\nНа канале "[{channel_name}]({channel_url})" вышло новое видео:'
