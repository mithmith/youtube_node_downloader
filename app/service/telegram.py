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
        self._bot_token = bot_token
        self._group_id = group_id
        self._queue = queue
        self._delay = delay
        self._users_ids = users_ids or []
        logger.info("Telegram bot created")

    def run(self):
        """Запускает поток для публикации сообщений из очереди."""
        process = Process(target=self._start)
        process.start()
        return process

    def _start(self):
        """Инициализация всех обработчиков и запуск бота."""
        application = Application.builder().token(self._bot_token).build()
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_message))
        application.add_handler(CommandHandler("start", self._start_command))
        # application.run_polling(allowed_updates=Update.ALL_TYPES)

        # Создаем задачи для асинхронного выполнения
        loop = asyncio.get_event_loop()
        loop.create_task(self._publish_messages(application.bot))
        # logger.info("Telegram bot is starting...")
        # loop.run_until_complete(application.run_polling(allowed_updates=Update.ALL_TYPES))

    def _start_async_loop(self, coro_func, *args, **kwargs):
        """Запускает событийный цикл для асинхронной функции."""
        asyncio.run(coro_func(*args, **kwargs))

    async def _publish_messages(self, bot: Bot):
        """Публикация сообщений из очереди каждые N секунд."""
        # bot = Bot(token=self._bot_token)
        logger.info("News feed Bot is running...")

        while True:
            try:
                # Получаем сообщение из очереди
                logger.debug("Checking queue")
                video: NewVideoSchema = self._queue.get(block=False, timeout=5)  # Ждём сообщение
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
                await asyncio.sleep(self._delay)
                continue
            except Exception as e:
                logger.error(f"Ошибка при отправке сообщения: {e}")

    async def _handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка входящих сообщений от пользователей."""
        user_id = update.effective_user.id
        full_username = update.effective_user.full_name
        text = update.message.text
        logger.debug(f"Received message from user {full_username} ({user_id}): {text}")

        # Проверяем, является ли сообщение ответом на сообщение бота
        reply_to_message: Message = update.message.reply_to_message
        if reply_to_message and reply_to_message.from_user and reply_to_message.from_user.id == context.bot.id:
            logger.debug("Message is a reply to the bot")

            # Пытаемся извлечь ID оригинального пользователя
            try:
                original_user_id = self._extract_original_user_id(reply_to_message.text)
            except Exception as e:
                logger.error(f"Failed to extract original user ID from reply: {e}")
                await context.bot.send_message(
                    chat_id=update.effective_chat.id, text="Не удалось определить пользователя для ответа."
                )
                return

            if original_user_id:
                # Отправляем сообщение оригинальному пользователю
                try:
                    await context.bot.send_message(
                        chat_id=original_user_id,
                        text=text,
                    )
                    logger.debug(f"Sent reply to original user {original_user_id}")
                except Exception as e:
                    logger.error(f"Failed to send reply to original user {original_user_id}: {e}")
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=f"Не удалось отправить сообщение пользователю {original_user_id}.",
                    )
                    return

                # Пересылаем сообщение всем администраторам, кроме оригинального пользователя
                for admin_id in self._users_ids:
                    if str(admin_id) != str(original_user_id) and str(admin_id) != str(user_id):
                        try:
                            await context.bot.send_message(
                                chat_id=admin_id,
                                text=(
                                    f"Ответ от {full_username} (tg://user?id={user_id}) "
                                    f"пользователю (id={original_user_id}):\n{text}"
                                ),
                                # parse_mode="Text",
                            )
                            logger.debug(f"Forwarded reply to admin {admin_id}")
                        except Exception as e:
                            logger.error(f"Failed to forward reply to admin {admin_id}: {e}")
                return

        # Если это не ответное сообщение, рассылаем его всем администраторам
        logger.debug("Message is not a reply. Forwarding to all admins.")
        for admin_id in self._users_ids:
            try:
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=(f"Сообщение от {full_username} (id={user_id}):\n{text}"),
                    # parse_mode="Text",
                )
                logger.debug(f"Forwarded message to admin {admin_id}")
            except Exception as e:
                logger.error(f"Failed to forward message to admin {admin_id}: {e}")

        # Подтверждаем отправителю, что его сообщение получено
        await update.message.reply_text("Ваше сообщение получено. Спасибо!")

    async def _start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /start."""
        await update.message.reply_text("Привет! Я Telegram-бот. Напишите мне что-нибудь.")

    def _format_telegram_message(self, channel_name, channel_url, video_title, video_url):
        """Форматирование сообщения в Markdown формате."""
        return f'**[{video_title}]({video_url})**\nНа канале "[{channel_name}]({channel_url})" вышло новое видео:'

    def _extract_original_user_id(self, text: str) -> str | None:
        """Извлекает ID оригинального пользователя из текста сообщения."""
        try:
            # Пытаемся найти строку вида `(id=123456789)`
            start_index = text.find("(id=") + 4
            end_index = text.find(")", start_index)
            if start_index > 3 and end_index > start_index:  # Убедимся, что индексы корректны
                user_id = text[start_index:end_index]
                return user_id if user_id.isdigit() else None
        except Exception as e:
            logger.error(f"Failed to extract user ID: {e}")
        return None
