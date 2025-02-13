import os

from loguru import logger
from telegram import Message, Update
from telegram.ext import ContextTypes
from telegram.helpers import escape_markdown

from app.config import settings
from app.integrations.telegram.utils import extract_original_user_id, format_telegram_message

MAX_TELEGRAM_VIDEO_SIZE = 50 * 1024 * 1024  # 50 MB


async def send_test_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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


async def send_test_shorts_video(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    video_path = "../test_shorts_video_w6CxKyVLtmo.mp4"
    channel_name = "Это базис"
    channel_url = "https://www.youtube.com/@eto_basis"
    video_title = "Почему власть боится бумажных стаканчиков и как это связано с Богородицей?"
    video_url = "https://www.youtube.com/shorts/w6CxKyVLtmo"

    # Проверяем размер видео
    if os.path.getsize(video_path) > MAX_TELEGRAM_VIDEO_SIZE:
        logger.error(
            f"Видео {video_url} слишком большое для Telegram! ({os.path.getsize(video_path) / (1024 * 1024):.2f} MB)"
        )
        return

    await context.bot.send_video(
        chat_id=settings.tg_admin_id,
        video=open(video_path, "rb"),
        caption=format_shorts_message(channel_name, channel_url, video_title, video_url),
        parse_mode="Markdown",
    )


def format_shorts_message(channel_name: str, channel_url: str, video_title: str, video_url: str):
    """Форматирование сообщения в Markdown формате."""
    return (
        f"🎥 [{escape_markdown(video_title)}]({video_url})\n"
        f"🎬 *Новое видео!*"
        f" На канале «[{escape_markdown(channel_name)}]({channel_url})»\n"
        + escape_markdown(f'\n#Shorts #YouTube #{channel_name.replace(" ", "_")}')
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка входящих сообщений от пользователей."""
    admin_users_ids = [settings.tg_admin_id]
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
            original_user_id = extract_original_user_id(reply_to_message.text)
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
            for admin_id in admin_users_ids:
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
    for admin_id in admin_users_ids:
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
