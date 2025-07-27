"""Telegram webhook entrypoint for MandiMonitor Bot."""

import logging
from threading import Thread
from telegram.ext import ApplicationBuilder

from bot.config import settings
from bot.handlers import setup_handlers
from bot import health

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


def main():
    """Main entry point for the bot application."""
    # Create Telegram application
    app = ApplicationBuilder().token(settings.TELEGRAM_TOKEN).build()
    setup_handlers(app)

    # Start Flask health server in background thread
    health_thread = Thread(
        target=lambda: health.app.run(host="0.0.0.0", port=8000, debug=False),
        daemon=True,
    )
    health_thread.start()
    logger.info("Health server started on port 8000")

    # Start Telegram bot polling
    logger.info("Starting Telegram bot...")
    app.run_polling()


if __name__ == "__main__":
    main()
