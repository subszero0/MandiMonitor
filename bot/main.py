"""Telegram webhook entrypoint for MandiMonitor Bot."""

from bot.config import settings
from bot.handlers import setup_handlers
from telegram.ext import ApplicationBuilder

app = ApplicationBuilder().token(settings.TELEGRAM_TOKEN).build()
setup_handlers(app)

if __name__ == "__main__":
    app.run_polling() 