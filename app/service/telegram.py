import asyncio
import os
import time
from asyncio import AbstractEventLoop
from multiprocessing import Process, Queue
from pathlib import Path
from queue import Empty

from telegram import Bot, Update
from telegram.error import TelegramError
from telegram.ext import Application
from telegram.helpers import escape_markdown
from jinja2 import Template, TemplateSyntaxError

from app.config import logger, settings
from app.integrations.telegram import get_telegram_handlers
from app.schema import NewVideoSchema, VideoDownloadSchema
from app.service.utils import get_channel_hashtag


class TelegramBotService:
    """Класс для публикации сообщений в Telegram."""

    def __init__(self, bot_token: str, group_id: str, msg_queue: Queue, shorts_queue: Queue = None, delay: int = 30):
        self._bot_token = bot_token
        self._group_id = group_id
        self._messages_queue = msg_queue
        self._shorts_queue = shorts_queue
        self._delay = delay  # Задержка между отправками сообщений с новыми видео
        self._max_retries = 3  # Максимальное количество попыток запуска бота и отправки сообщений
        self._retry_delay = 5  # Задержка между неудачными попытками (в секундах)
        # self._repository = YoutubeVideoRepository(session=Session())
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
                    loop.create_task(self._publish_messages(application.bot))
                if settings.run_tg_bot_shorts_publish:
                    loop.create_task(self._publish_shorts_videos(application.bot))

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
        await asyncio.sleep(5)
        logger.info("News feed Bot is running...")

        while True:
            try:
                # Получаем сообщение из очереди
                logger.debug("(TGBot) Checking messages queue...")
                video: NewVideoSchema = self._messages_queue.get(block=False, timeout=5)  # Ждём сообщение
                logger.debug(f"video={video}")

                message = self._format_newvideo_message(
                    video.channel_name, video.channel_url, video.video_title, video.video_url
                )
                logger.info(f"(TGBot) Sending message to {self._group_id}:\n{message}")

                await self._send_message_with_retries(bot, chat_id=self._group_id, text=message)

                # Задержка между отправками сообщений
                await asyncio.sleep(self._delay)
            except Empty:
                # Если очередь пуста после таймаута, ничего не делаем и продолжаем ждать
                await asyncio.sleep(self._delay)
                continue
            except Exception as e:
                logger.error(f"(TGBot) Ошибка при отправке сообщения: {e}")

    async def _publish_shorts_videos(self, bot: Bot):
        """Публикация shorts из очереди каждые N секунд."""
        if self._shorts_queue is None:
            return
        await asyncio.sleep(5)
        logger.info("Shorts publisher Bot is running...")

        while True:
            try:
                # Получаем сообщение из очереди
                logger.debug("(TGBot) Checking shorts queue...")
                video: VideoDownloadSchema = self._shorts_queue.get(block=False, timeout=10)  # Ждём сообщение
                logger.debug(f"video={video}")

                message = self._format_shorts_message(
                    video.channel_name, video.channel_url, video.video_title, video.video_url
                )
                logger.info(f"(TGBot) Sending message to {self._group_id}:\n{message}")

                await self._send_message_with_retries(
                    bot, self._group_id, message, video_path=Path(video.video_file_download_path)
                )

                # Задержка между отправками сообщений
                await asyncio.sleep(self._delay)
            except Empty:
                # Если очередь пуста после таймаута, ничего не делаем и продолжаем ждать
                await asyncio.sleep(self._delay)
                continue
            except Exception as e:
                logger.error(f"(TGBot) Ошибка при отправке сообщения: {e}")

    async def _send_message_with_retries(self, bot: Bot, chat_id: str, text: str, video_path: Path = None):
        """
        Отправляет сообщение в Telegram с заданным числом повторных попыток.

        :param bot: Экземпляр бота Telegram.
        :param chat_id: ID чата, куда отправляется сообщение.
        :param text: Текст сообщения.
        """
        for attempt in range(1, self._max_retries + 1):
            try:
                if video_path is not None and video_path.exists():
                    logger.debug("(TGBot) Sending video...")
                    await bot.send_video(
                        chat_id=chat_id,
                        video=open(video_path, "rb"),
                        caption=text,
                        parse_mode="Markdown",
                        pool_timeout=180,
                        read_timeout=180,
                        write_timeout=180,
                        connect_timeout=180,
                    )
                    logger.info("(TGBot) Видео успешно отправлено")
                elif text:
                    await bot.send_message(
                        chat_id=chat_id,
                        text=text,
                        parse_mode="Markdown",
                    )
                    # self._repository.update_tg_post_date(video_id)
                    logger.info("(TGBot) Сообщение успешно отправлено")
                return  # Успешная отправка, выходим из функции
            except asyncio.TimeoutError:
                logger.error(f"Timeout error при отправке сообщения (попытка {attempt} из {self._max_retries})")
            except TelegramError as te:
                logger.error(f"Telegram API error (попытка {attempt} из {self._max_retries}): {te}")
            except Exception as e:
                logger.error(
                    f"Неизвестная ошибка при отправке сообщения (попытка {attempt} из {self._max_retries}): {e}"
                )

            if attempt < self._max_retries:
                logger.info(f"Повторная попытка отправки сообщения через {self._retry_delay} секунд...")
                await asyncio.sleep(self._retry_delay)

        logger.error("Не удалось отправить сообщение после всех попыток")

    @staticmethod
    def render_template(template_path: Path, **kwargs) -> str:
        """Загружает и рендерит шаблон с подстановкой значений."""
        if not template_path.exists():
            raise FileNotFoundError(f"Шаблон не найден: {template_path}")

        try:
            with open(template_path, "r", encoding="utf-8") as f:
                template_content = f.read()

            # Экранируем переменные
            safe_kwargs = {
                key: escape_markdown(value, version=2) if key not in {"channel_hashtag"} else value
                for key, value in kwargs.items()
            }

            template = Template(template_content)
            return template.render(**safe_kwargs)
        except TemplateSyntaxError as e:
            raise ValueError(f"Ошибка в шаблоне {template_path}: {e}")

    def _format_newvideo_message(self, channel_name: str, channel_url: str, video_title: str, video_url: str):
        """Форматирование сообщения в Markdown формате."""
        return self.render_template(
            settings.tg_new_video_template,
            video_title=video_title,
            video_url=video_url,
            channel_name=channel_name,
            channel_url=channel_url,
            channel_hashtag=get_channel_hashtag(channel_name),
        )

    def _format_shorts_message(self, channel_name: str, channel_url: str, video_title: str, video_url: str):
        """Форматирование сообщения в Markdown формате."""
        return self.render_template(
            settings.tg_shorts_template,
            video_title=video_title,
            video_url=video_url,
            channel_name=channel_name,
            channel_url=channel_url,
            channel_hashtag=get_channel_hashtag(channel_name),
        )
