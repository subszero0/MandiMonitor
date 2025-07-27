"""Telegram bot command handlers."""

import logging
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command - welcome message to verify bot is working.

    Args:
        update: Telegram update object
        context: Bot context for the handler
    """
    await update.message.reply_text("Bot alive 👋")


def setup_handlers(app) -> None:
    """Set up all Telegram bot command handlers.

    Args:
        app: telegram.ext.Application instance
    """
    # Register command handlers
    app.add_handler(CommandHandler("start", start))

    logger.info("Telegram handlers registered: /start")
