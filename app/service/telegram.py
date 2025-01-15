import asyncio
import time
from asyncio import AbstractEventLoop
from multiprocessing import Process, Queue
from queue import Empty

from loguru import logger
from telegram import Bot, Update
from telegram.error import TelegramError
from telegram.ext import Application

from app.config import settings
from app.integrations.telegram import get_telegram_handlers
from app.schema import NewVideoSchema


class TelegramBotService:
    """Класс для публикации сообщений в Telegram."""

    def __init__(self, bot_token: str, group_id: str, queue: Queue, delay: int = 30):
        self._bot_token = bot_token
        self._group_id = group_id
        self._queue = queue
        self._delay = delay  # Задержка между отправками сообщений с новыми видео
        self._max_retries = 3  # Максимальное количество попыток запуска бота и отправки сообщений
        self._retry_delay = 5  # Задержка между неудачными попытками (в секундах)
        logger.info("Telegram bot is created")

    def run(self):
        """Запускает поток для публикации сообщений из очереди."""
        process = Process(target=self._start)
        process.start()
        return process

    def _start(self):
        """Инициализация всех обработчиков и запуск бота."""
        for attempt in range(1, self._max_retries + 1):
            try:
                application = Application.builder().token(self._bot_token).build()
                for handler in get_telegram_handlers():
                    application.add_handler(handler)

                # Создаём новый event loop для асинхронных задач
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                if settings.monitor_new:
                    # Добавляем задачу публикации сообщений
                    loop.create_task(self._publish_messages(application.bot))

                try:
                    logger.info("Starting Telegram bot...")
                    application.run_polling(
                        allowed_updates=Update.ALL_TYPES,
                        read_timeout=60,
                        write_timeout=60,
                        connect_timeout=60,
                        pool_timeout=60,
                        timeout=60,
                    )
                except Exception as e:
                    logger.error(f"Error during polling: {e}")
                    raise
                break
            except KeyboardInterrupt:
                logger.info("Keyboard interrupt detected, shutting down...")
            except TelegramError as te:
                logger.error(f"Telegram API error: {te}")
            except Exception as e:
                logger.error(f"Unexpected error in Telegram bot: {e}")
            finally:
                self._graceful_shutdown(application, loop)

            # Если это не последняя попытка, ждем перед повтором
            if attempt < self._max_retries:
                logger.warning(f"Повторная попытка запуска через {attempt*self._retry_delay} секунд...")
                time.sleep(attempt * self._retry_delay)
            else:
                logger.error("Не удалось запустить Telegram бота после всех попыток.")
                raise RuntimeError("Telegram bot failed to start after multiple retries.")

    def _start_async_loop(self, coro_func, *args, **kwargs):
        """Запускает событийный цикл для асинхронной функции."""
        asyncio.run(coro_func(*args, **kwargs))

    def _graceful_shutdown(self, application: Application, loop: AbstractEventLoop):
        """Корректно завершает работу бота и цикла событий."""
        try:
            logger.info("Shutting down Telegram bot...")
            if not loop.is_closed():
                loop.run_until_complete(application.shutdown())
                loop.run_until_complete(loop.shutdown_asyncgens())
                loop.close()
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")

    async def _publish_messages(self, bot: Bot):
        """Публикация сообщений из очереди каждые N секунд."""
        await asyncio.sleep(10)
        logger.info("News feed Bot is running...")

        while True:
            try:
                # Получаем сообщение из очереди
                logger.debug("Telegram bot is checking messages queue")
                video: NewVideoSchema = self._queue.get(block=False, timeout=5)  # Ждём сообщение
                logger.debug(f"video={video}")

                message = self._format_telegram_message(
                    video.channel_name, video.channel_url, video.video_title, video.video_url
                )
                logger.debug(f"Sending message to {self._group_id}:\n{message}")

                await self._send_message_with_retries(bot=bot, chat_id=self._group_id, text=message)

                # Задержка между отправками сообщений
                await asyncio.sleep(self._delay)
            except Empty:
                # Если очередь пуста после таймаута, ничего не делаем и продолжаем ждать
                await asyncio.sleep(self._delay)
                continue
            except Exception as e:
                logger.error(f"Ошибка при отправке сообщения: {e}")

    async def _send_message_with_retries(self, bot: Bot, chat_id: str, text: str):
        """
        Отправляет сообщение в Telegram с заданным числом повторных попыток.

        :param bot: Экземпляр бота Telegram.
        :param chat_id: ID чата, куда отправляется сообщение.
        :param text: Текст сообщения.
        """
        for attempt in range(1, self._max_retries + 1):
            try:
                await bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    parse_mode="Markdown",
                )
                logger.info("Сообщение успешно отправлено")
                return  # Успешная отправка, выходим из функции
            except TelegramError as te:
                logger.error(f"Telegram API error (попытка {attempt} из {self._max_retries}): {te}")
            except asyncio.TimeoutError:
                logger.error(f"Timeout error при отправке сообщения (попытка {attempt} из {self._max_retries})")
            except Exception as e:
                logger.error(
                    f"Неизвестная ошибка при отправке сообщения (попытка {attempt} из {self._max_retries}): {e}"
                )

            if attempt < self._max_retries:
                logger.info(f"Повторная попытка отправки сообщения через {self._retry_delay} секунд...")
                await asyncio.sleep(self._retry_delay)

        logger.error("Не удалось отправить сообщение после всех попыток")

    def _format_telegram_message(self, channel_name, channel_url, video_title, video_url):
        """Форматирование сообщения в Markdown формате."""
        return f'**[{video_title}]({video_url})**\nНа канале "[{channel_name}]({channel_url})" вышло новое видео:'
