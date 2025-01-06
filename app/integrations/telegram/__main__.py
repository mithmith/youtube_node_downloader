import logging

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters

from app.config import settings
from app.integrations.telegram.commands import start
from app.integrations.telegram.messages import send_message

# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.INFO)
logger = logging.getLogger(__name__)


def main() -> None:
    """Starting telegram bot."""
    application = Application.builder().token(settings.tg_bot_token).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, send_message))

    logger.info("Starting Telegram bot...")
    logger.info("Press Ctrl+C to stop the bot.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
