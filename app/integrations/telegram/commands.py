from telegram import Update
from telegram.ext import ContextTypes


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    await update.message.reply_html(rf"Hi {user.mention_html()}!")


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка команды /start."""
    await update.message.reply_text("Привет! Я Telegram-бот. Напишите мне что-нибудь.")
