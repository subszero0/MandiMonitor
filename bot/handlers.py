"""Telegram bot command handlers."""

import logging

from sqlmodel import Session
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes

from .smart_alerts import SmartAlertEngine
from .affiliate import build_affiliate_url
from .cache_service import engine
from .models import Click

logger = logging.getLogger(__name__)

# Initialize SmartAlertEngine once at module level
smart_alerts = SmartAlertEngine()


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
/recommendations - Get AI-powered personalized suggestions 🤖
/insights - View market insights and AI analysis 🧠
/help - Show this help message  
/status - Check bot and system status
/about - Information about this bot

🚧 **Coming Soon:**
/list - View your active price watches
/admin - Admin dashboard (authorized users only)

💡 **AI Features:**
Get smarter recommendations based on your preferences and behavior!
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

**Features:**
• 📊 Real-time price monitoring ✅
• 🔔 Smart deal notifications ✅  
• 📈 Price history tracking ✅
• 💰 Affiliate link support ✅
• 📱 Easy Telegram interface ✅
• 🤖 AI-powered recommendations ✅
• 🎯 Personalized deal insights ✅
• 📦 Smart inventory alerts ✅

**Technology:**
• Python 3.12 + FastAPI
• SQLModel + SQLite Database
• Amazon PA-API integration
• Machine Learning (scikit-learn)
• AI-powered predictions
• Docker containerized

**Status:** 🚀 Production Ready with AI Features!

Built with ❤️ for deal hunters!
    """
    await update.message.reply_text(about_msg, parse_mode="Markdown")


async def recommendations_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /recommendations command - show AI-powered personalized recommendations.

    Args:
    ----
        update: Telegram update object
        context: Bot context for the handler

    """
    from .cache_service import engine
    from .models import User
    from sqlmodel import Session, select
    
    try:
        # Get or create user
        tg_user_id = update.effective_user.id
        
        with Session(engine) as session:
            user = session.exec(
                select(User).where(User.tg_user_id == tg_user_id)
            ).first()
            
            if not user:
                # Create new user
                user = User(tg_user_id=tg_user_id)
                session.add(user)
                session.commit()
                session.refresh(user)
        
        # Generate AI recommendations
        recommendations_data = await smart_alerts.generate_personalized_recommendations(user.id)
        
        if recommendations_data["status"] == "success":
            message_data = recommendations_data["message"]
            await update.message.reply_text(
                message_data["caption"],
                reply_markup=message_data["keyboard"],
                parse_mode="Markdown"
            )
        elif recommendations_data["status"] == "no_recommendations":
            await update.message.reply_text(
                "🤖 **Getting to know you!**\n\n"
                "I don't have enough data about your preferences yet. "
                "Try creating some price watches with /watch to help me understand what you like!\n\n"
                "The more you use the bot, the better my recommendations will become! 🎯",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(
                "⚠️ **Recommendations temporarily unavailable**\n\n"
                "I'm having trouble generating recommendations right now. "
                "Please try again later or use /watch to track specific products!",
                parse_mode="Markdown"
            )
            
    except Exception as e:
        logger.error("Error in recommendations command: %s", e)
        await update.message.reply_text(
            "❌ **Error generating recommendations**\n\n"
            "Something went wrong. Please try again later or contact support.",
            parse_mode="Markdown"
        )


async def insights_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /insights command - show market insights and AI analysis.

    Args:
    ----
        update: Telegram update object
        context: Bot context for the handler

    """
    try:
        insights_msg = """
🧠 **AI Market Insights**

**Your Shopping Intelligence:**
• 📊 Personalized deal predictions
• 🎯 Interest-based recommendations  
• 📈 Price trend analysis
• 📦 Smart inventory alerts
• 💡 Category exploration suggestions

**How it works:**
🤖 I analyze your browsing patterns, price preferences, and market trends to provide intelligent insights.

**Available Commands:**
/recommendations - Get personalized product suggestions
/watch - Create smart price alerts with AI insights

**Coming Soon:**
• Weekly market roundups
• Seasonal deal predictions
• Category trend analysis
• Budget optimization tips

💡 **Tip:** The more you interact with me, the smarter my recommendations become!
        """
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🤖 Get Recommendations", callback_data="get_recommendations"),
                InlineKeyboardButton("📊 View Analytics", callback_data="view_analytics")
            ],
            [
                InlineKeyboardButton("⚙️ AI Preferences", callback_data="ai_preferences"),
                InlineKeyboardButton("❓ Learn More", callback_data="learn_ai_features")
            ]
        ])
        
        await update.message.reply_text(
            insights_msg, 
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error("Error in insights command: %s", e)
        await update.message.reply_text(
            "❌ Error loading insights. Please try again later.",
            parse_mode="Markdown"
        )


async def ai_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle AI-related callback queries.

    Args:
    ----
        update: Telegram update object with callback query
        context: Bot context

    """
    from .cache_service import engine
    from .models import User
    from sqlmodel import Session, select
    
    query = update.callback_query
    await query.answer()
    
    try:
        if query.data == "get_recommendations":
            # Get user and generate recommendations
            tg_user_id = update.effective_user.id
            
            with Session(engine) as session:
                user = session.exec(
                    select(User).where(User.tg_user_id == tg_user_id)
                ).first()
                
                if user:
                    recommendations_data = await smart_alerts.generate_personalized_recommendations(user.id)
                    
                    if recommendations_data["status"] == "success":
                        message_data = recommendations_data["message"]
                        await query.edit_message_text(
                            message_data["caption"],
                            reply_markup=message_data["keyboard"],
                            parse_mode="Markdown"
                        )
                    else:
                        await query.edit_message_text(
                            "🤖 I need more data about your preferences. Try creating some watches first!",
                            parse_mode="Markdown"
                        )
                else:
                    await query.edit_message_text(
                        "Please use /start first to initialize your account.",
                        parse_mode="Markdown"
                    )
                    
        elif query.data == "view_analytics":
            await query.edit_message_text(
                "📊 **Your Shopping Analytics**\n\n"
                "Analytics dashboard coming soon! This will show:\n"
                "• Your deal success rate\n"
                "• Favorite categories\n"
                "• Savings achieved\n"
                "• AI prediction accuracy\n\n"
                "Use /recommendations to get personalized suggestions now!",
                parse_mode="Markdown"
            )
            
        elif query.data == "ai_preferences":
            await query.edit_message_text(
                "⚙️ **AI Preferences**\n\n"
                "Customize your AI experience:\n"
                "• Recommendation frequency\n"
                "• Preferred categories\n"
                "• Price range preferences\n"
                "• Notification types\n\n"
                "Advanced preference management coming soon!\n"
                "For now, your preferences are learned automatically from your interactions.",
                parse_mode="Markdown"
            )
            
        elif query.data == "learn_ai_features":
            await query.edit_message_text(
                "💡 **How AI Enhances Your Experience**\n\n"
                "🧠 **Smart Learning:** I analyze your watch patterns, clicked products, and preferences\n"
                "🎯 **Personalization:** Recommendations tailored specifically to your interests\n"
                "📊 **Deal Intelligence:** AI predicts deal success probability\n"
                "📦 **Inventory Alerts:** Smart notifications before items go out of stock\n"
                "📈 **Market Trends:** Price prediction and trend analysis\n\n"
                "Start with /watch to help me learn your preferences!",
                parse_mode="Markdown"
            )
            
        else:
            await query.edit_message_text("Unknown action. Please try again.")
            
    except Exception as e:
        logger.error("Error in AI callback handler: %s", e)
        await query.edit_message_text(
            "❌ Error processing request. Please try again later.",
            parse_mode="Markdown"
        )


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

    # Parse callback data: "click:watch_id:asin"
    try:
        _, watch_id_str, asin = query.data.split(":", 2)
        watch_id = int(watch_id_str)
    except (ValueError, IndexError):
        await query.answer("❌ Invalid link. Please try again.")
        return

    # Log the click
    with Session(engine) as session:
        click = Click(watch_id=watch_id, asin=asin)
        session.add(click)
        session.commit()

    # Redirect to affiliate URL with cache_time=0
    affiliate_url = build_affiliate_url(asin)
    
    # Answer callback query with URL redirect (this opens the URL)
    await query.answer(url=affiliate_url, cache_time=0)


async def handle_text_message(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle free text messages intelligently.

    Args:
    ----
        update: Telegram update object
        context: Bot context
    """
    text = update.message.text.strip()

    # Ignore empty messages or messages that look like commands
    if not text or text.startswith("/"):
        return
    
    text_lower = text.lower()
    
    # Check if this is an Amazon link - handle it specially
    if "amazon." in text_lower or "amzn.to" in text_lower:
        # This is an Amazon link, process it directly
        context.args = text.split()
        from .watch_flow import start_watch
        await start_watch(update, context)
        return
    
    # Check if this looks like a question or conversation rather than a product request
    question_patterns = [
        "what happened",
        "what's wrong",
        "what is this",
        "why",
        "how",
        "can you",
        "do you",
        "are you",
        "is this",
        "help me",
        "what's going on",
        "explain",
        "tell me",
        "?",  # Any message ending with question mark
    ]
    
    # If the message looks like a question or conversational, provide help instead
    if any(pattern in text_lower for pattern in question_patterns) or text.endswith("?"):
        help_msg = """
🤔 **I see you have a question!**

I'm designed to help you track product prices. Here's what I can do:

**To create a price watch, send me:**
• Product descriptions: `Samsung 27 inch gaming monitor`
• Amazon links: `https://amazon.in/dp/B09XYZ1234`
• Specific requests: `iPhone 15 under 50000 with 20% discount`

**Available commands:**
/help - Show all commands
/status - Check bot status
/watch - Create a new price watch

💡 **Tip:** Just type what you're looking for and I'll help you set up price alerts!
        """
        await update.message.reply_text(help_msg, parse_mode="Markdown")
        return
    
    # Check if text is too short to be a meaningful product search (but allow URLs)
    if len(text.split()) < 2 and not ("http" in text_lower):
        await update.message.reply_text(
            "🔍 **Need more details!**\n\n"
            "Please provide more information about the product you want to track.\n\n"
            "**Examples:**\n"
            "• `Samsung gaming monitor`\n"
            "• `Apple iPhone 15`\n"
            "• `Boat headphones under 3000`\n"
            "• `https://amazon.in/dp/B09XYZ1234`",
            parse_mode="Markdown"
        )
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
    app.add_handler(CommandHandler("recommendations", recommendations_command))
    app.add_handler(CommandHandler("insights", insights_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("about", about_command))

    # Register callback handlers for watch creation flow
    app.add_handler(
        CallbackQueryHandler(handle_callback, pattern="^(brand:|disc:|price:|mode:)")
    )

    # Register AI callback handlers
    app.add_handler(
        CallbackQueryHandler(ai_callback_handler, pattern="^(get_recommendations|view_analytics|ai_preferences|learn_ai_features|view_all_recommendations|update_preferences|inventory_details:).*$")
    )

    # Register click handler for affiliate link tracking
    app.add_handler(
        CallbackQueryHandler(click_handler, pattern=r"^click:\d+:[A-Z0-9]+$")
    )

    # Register message handler for free text (should be last to avoid conflicts)
    from telegram.ext import MessageHandler, filters

    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message)
    )

    logger.info(
        "Telegram handlers registered: /start, /watch, /recommendations, /insights, /help, /status, /about, ai_callbacks, callbacks, click_handler, text_messages"
    )
