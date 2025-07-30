"""Telegram bot command handlers."""

import logging

from telegram import Update
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes

logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command - welcome message to verify bot is working.

    Args:
    ----
        update: Telegram update object
        context: Bot context for the handler

    """
    welcome_msg = """
🤖 **MandiMonitor Bot** - Your Price Tracking Assistant!

👋 Hi! I'm here to help you monitor product prices and find great deals.

**Available Commands:**
/watch - Create price monitoring alerts  
/help - Show this help message
/status - Check bot status
/about - About this bot

🚀 **Start tracking prices now with /watch!**

For now, you can interact with me using the commands above.
    """
    await update.message.reply_text(welcome_msg, parse_mode="Markdown")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command - show available commands.

    Args:
    ----
        update: Telegram update object
        context: Bot context for the handler

    """
    help_msg = """
🔧 **Available Commands:**

/start - Welcome message and overview
/watch - Create price monitoring alerts ✨ 
/help - Show this help message  
/status - Check bot and system status
/about - Information about this bot

🚧 **Coming Soon:**
/list - View your active price watches
/admin - Admin dashboard (authorized users only)

💡 **Need Help?**
This bot is in development. More features coming soon!
    """
    await update.message.reply_text(help_msg, parse_mode="Markdown")


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /status command - show bot status.

    Args:
    ----
        update: Telegram update object
        context: Bot context for the handler

    """
    from bot.cache_service import get_price

    # Test database connection
    try:
        # Try a simple database operation
        from sqlalchemy import text

        from bot.cache_service import engine

        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_status = "✅ Connected"
    except Exception as e:
        db_status = f"❌ Error: {str(e)[:50]}..."

    # Test price fetching
    try:
        # Try to fetch a price (will test both PA-API and scraper)
        get_price("B08N5WRWNW")
        price_status = "✅ Working"
    except Exception as e:
        if "PA-API" in str(e) and "scraper" in str(e):
            price_status = "⚠️ PA-API failed, Scraper failed"
        elif "PA-API" in str(e):
            price_status = "⚠️ PA-API failed, Scraper OK"
        else:
            price_status = f"❌ Error: {str(e)[:30]}..."

    status_msg = f"""
🤖 **Bot Status Report**

**Core Systems:**
• Telegram Bot: ✅ Online
• Database: {db_status}
• Price Fetching: {price_status}
• Health Endpoint: ✅ Available at /health

**Configuration:**
• PA-API: {"✅ Configured" if context.bot_data.get('paapi_configured') else "⚠️ Not configured"}
• Admin Interface: 🚧 In development

**Version:** Development Build
**Uptime:** Running since bot start
    """
    await update.message.reply_text(status_msg, parse_mode="Markdown")


async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /about command - show bot information.

    Args:
    ----
        update: Telegram update object
        context: Bot context for the handler

    """
    about_msg = """
🤖 **MandiMonitor Bot**

**What I Do:**
I help you track product prices on Amazon India and notify you when prices drop!

**Features (Coming Soon):**
• 📊 Real-time price monitoring
• 🔔 Instant deal notifications  
• 📈 Price history tracking
• 💰 Affiliate link support
• 📱 Easy Telegram interface

**Technology:**
• Python 3.12 + FastAPI
• SQLModel + SQLite Database
• Amazon PA-API integration
• Playwright web scraping
• Docker containerized

**Status:** 🚧 In Active Development

Built with ❤️ for deal hunters!
    """
    await update.message.reply_text(about_msg, parse_mode="Markdown")


def setup_handlers(app) -> None:
    """Set up all Telegram bot command handlers.

    Args:
    ----
        app: telegram.ext.Application instance

    """
    from .watch_flow import handle_callback, start_watch

    # Register command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("watch", start_watch))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("about", about_command))

    # Register callback handlers for watch creation flow
    app.add_handler(
        CallbackQueryHandler(handle_callback, pattern="^(brand:|disc:|price:)")
    )

    logger.info(
        "Telegram handlers registered: /start, /watch, /help, /status, /about, callbacks"
    )
