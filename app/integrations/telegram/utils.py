from typing import Optional

from loguru import logger


def format_telegram_message(channel_name, channel_url, video_title, video_url):
    """Форматирование сообщения в Markdown формате."""
    return f"**[{video_title}]({video_url})**\n" f"На канале [{channel_name}]({channel_url}) вышло новое видео:"


def extract_original_user_id(text: str) -> Optional[str]:
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
