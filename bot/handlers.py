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


async def click_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle click-out tracking for affiliate links.

    Args:
    ----
        update: Telegram update object with callback query
        context: Bot context

    """
    from sqlmodel import Session
    from .cache_service import engine
    from .models import Click
    from .affiliate import build_affiliate_url

    query = update.callback_query
    await query.answer()

    # Parse callback data: "click:watch_id:asin"
    try:
        _, watch_id_str, asin = query.data.split(":", 2)
        watch_id = int(watch_id_str)
    except (ValueError, IndexError):
        await query.edit_message_text("❌ Invalid link. Please try again.")
        return

    # Log the click
    with Session(engine) as session:
        click = Click(watch_id=watch_id, asin=asin)
        session.add(click)
        session.commit()

    # Redirect to affiliate URL with cache_time=0
    affiliate_url = build_affiliate_url(asin)
    await query.answer(url=affiliate_url, cache_time=0)


async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle free text messages as watch creation input.
    
    Args:
    ----
        update: Telegram update object
        context: Bot context
    """
    # Treat free text as watch creation input
    text = update.message.text.strip()
    
    # Ignore empty messages or messages that look like commands
    if not text or text.startswith('/'):
        return
        
    # Convert the text message into a /watch command format
    context.args = text.split()
    
    # Import and call the watch creation handler
    from .watch_flow import start_watch
    await start_watch(update, context)


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

    # Register click handler for affiliate link tracking
    app.add_handler(
        CallbackQueryHandler(click_handler, pattern=r"^click:\d+:[A-Z0-9]+$")
    )
    
    # Register message handler for free text (should be last to avoid conflicts)
    from telegram.ext import MessageHandler, filters
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))

    logger.info(
        "Telegram handlers registered: /start, /watch, /help, /status, /about, callbacks, click_handler, text_messages"
    )
