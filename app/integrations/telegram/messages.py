from telegram import Update
from telegram.ext import ContextTypes

from app.config import settings


def format_telegram_message(channel_name, channel_url, video_title, video_url):
    """Форматирование сообщения в Markdown формате."""
    return f"**[{video_title}]({video_url})**\n" f"На канале [{channel_name}]({channel_url}) вышло новое видео:"


async def send_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправить тестовое сообщение в группу Telegram."""
    channel_name = "Lenin Crew"
    channel_url = "https://www.youtube.com/@lenincrew"
    video_title = "Николай Некрасов – На волге | LC. Культура"
    video_url = "https://www.youtube.com/watch?v=le94-lVtrys"

    # Отправляем сообщение в группу
    await context.bot.send_message(
        chat_id=settings.tg_group_id,
        text=format_telegram_message(channel_name, channel_url, video_title, video_url),
        parse_mode="Markdown",
    )

    # Подтверждение отправки пользователю
    await update.message.reply_text("Сообщение отправлено в группу.")
