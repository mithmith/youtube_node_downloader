import asyncio
from multiprocessing import Process, Queue
from queue import Empty

from loguru import logger
from telegram import Bot, Message, Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from app.schema import NewVideoSchema


class TelegramBotService:
    """Класс для публикации сообщений в Telegram."""

    def __init__(self, bot_token: str, group_id: str, queue: Queue, delay: int = 30, users_ids: list[str] = None):
        logger.info("Creating telegram bot...")
        self._bot_token = bot_token
        self._group_id = group_id
        self._queue = queue
        self._delay = delay
        self._users_ids = users_ids or []
        self._application = Application.builder().token(self._bot_token).build()

    def run(self):
        """Запускает поток для публикации сообщений из очереди."""
        process = Process(target=self._start_async_loop, args=(self._start,))
        process.start()
        return process

    def _start_async_loop(self, coro_func, *args, **kwargs):
        """Запускает событийный цикл для асинхронной функции."""
        asyncio.run(coro_func(*args, **kwargs))

    async def _start(self):
        """Инициализация всех обработчиков и запуск бота."""
        self._application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_message))
        self._application.add_handler(CommandHandler("start", self._start_command))

        asyncio.create_task(self._publish_messages())
        logger.info("Telegram bot is starting...")
        await self._application.run_polling()

    async def _publish_messages(self):
        """Публикация сообщений из очереди каждые N секунд."""
        bot = Bot(token=self._bot_token)
        logger.info("News feed Bot is running...")

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
                await asyncio.sleep(self._delay)
            except Empty:
                # Если очередь пуста после таймаута, ничего не делаем и продолжаем ждать
                continue
            except Exception as e:
                logger.error(f"Ошибка при отправке сообщения: {e}")

    async def _handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка входящих сообщений от пользователей."""
        user_id = update.effective_user.id
        full_username = update.effective_user.full_name
        text = update.message.text
        logger.info(f"Received message from user {full_username} ({user_id}): {text}")

        # Проверяем, является ли сообщение ответом
        reply_to_message: Message = update.message.reply_to_message
        if reply_to_message and reply_to_message.from_user.id == context.bot.id:
            # Ответ на сообщение, отправленное ботом
            original_user_id = self._extract_original_user_id(reply_to_message.text)
            if original_user_id:
                # 1. Отправляем сообщение тому пользователю, который написал
                try:
                    await context.bot.send_message(
                        chat_id=original_user_id,
                        text=text,  # Отправляем только текст ответа
                    )
                    logger.info(f"Sent reply to original user {original_user_id}")
                except Exception as e:
                    logger.error(f"Failed to send reply to original user {original_user_id}: {e}")

                # 2. Отправляем сообщение остальным пользователям из self._users_ids
                for user in self._users_ids:
                    if user != str(original_user_id):
                        try:
                            await context.bot.send_message(
                                chat_id=user,
                                text=(
                                    f"Ответ от [{full_username}](tg://user?id={user_id}) "
                                    f"пользователю [{original_user_id}](tg://user?id={original_user_id}):\n{text}"
                                ),
                                parse_mode="Markdown",
                            )
                            logger.info(f"Forwarded reply to user {user}")
                        except Exception as e:
                            logger.error(f"Failed to forward reply to user {user}: {e}")
                return

        # Если это не ответ, обрабатываем как обычное сообщение
        for user in self._users_ids:
            try:
                await context.bot.send_message(
                    chat_id=user,
                    text=(f"Сообщение от [{full_username}](tg://user?id={user_id}):\n{text}"),
                    parse_mode="Markdown",
                )
                logger.info(f"Forwarded message to user {user}")
            except Exception as e:
                logger.error(f"Failed to forward message to user {user}: {e}")

        # Ответ отправителю
        await update.message.reply_text("Ваше сообщение получено. Спасибо!")

    async def _start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /start."""
        await update.message.reply_text("Привет! Я Telegram-бот. Напишите мне что-нибудь.")

    def _format_telegram_message(self, channel_name, channel_url, video_title, video_url):
        """Форматирование сообщения в Markdown формате."""
        return f'**[{video_title}]({video_url})**\nНа канале "[{channel_name}]({channel_url})" вышло новое видео:'

    def _extract_original_user_id(self, reply_text: str) -> str:
        """Извлекает ID пользователя из текста сообщения."""
        # Предполагаем, что сообщение имеет формат:
        # "Сообщение от [full_username](tg://user?id=user_id):\nтекст"
        import re

        match = re.search(r"tg://user\?id=(\d+)", reply_text)
        if match:
            return match.group(1)
        return None
