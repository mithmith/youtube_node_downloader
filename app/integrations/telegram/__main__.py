import logging

from telegram import Update
from telegram.ext import Application, BaseHandler, CommandHandler, MessageHandler, filters

from app.config import settings
from app.integrations.telegram.commands import start, start_command
from app.integrations.telegram.messages import handle_message, send_test_message

# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.INFO)
logger = logging.getLogger(__name__)


def get_telegram_handlers(test_mode: bool = False) -> list[BaseHandler]:
    """Return list of telegram handlers."""
    if test_mode:
        return [
            CommandHandler("start", start),
            MessageHandler(filters.TEXT & ~filters.COMMAND, send_test_message),
        ]
    return [
        CommandHandler("start", start_command),
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message),
    ]


def main() -> None:
    """Starting telegram bot."""
    application = Application.builder().token(settings.tg_bot_token).build()
    for handler in get_telegram_handlers(test_mode=True):
        application.add_handler(handler)

    logger.info("Starting Telegram bot...")
    logger.info("Press Ctrl+C to stop the bot.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
