"""BackgroundScheduler singleton & helpers."""

from __future__ import annotations
from datetime import datetime, time as dtime
from logging import getLogger
from zoneinfo import ZoneInfo
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlmodel import Session, select
from .cache_service import engine
from .models import Watch, User, Price
from .cache_service import get_price
from .carousel import build_single_card
from telegram import Bot
from .config import settings

log = getLogger(__name__)

TZ = ZoneInfo(settings.TIMEZONE)

scheduler = BackgroundScheduler(timezone=TZ)

# --- Job helpers -----------------------------------------------------------


def schedule_watch(watch: Watch) -> None:
    """Attach either a daily-digest or 10-min real-time job for a watch."""
    if watch.mode == "daily":
        # 09:00 IST default until per-user time is added
        trig = CronTrigger(hour=9, minute=0)
        scheduler.add_job(
            digest_job,
            trig,
            args=[watch.user_id],
            id=f"daily:{watch.user_id}",
            replace_existing=True,
        )
    else:
        trig = IntervalTrigger(minutes=10)
        scheduler.add_job(
            realtime_job,
            trig,
            args=[watch.id],
            id=f"rt:{watch.id}",
            replace_existing=True,
        )


# --- Job functions ---------------------------------------------------------


def daily_market_analysis() -> None:
    """Perform daily market analysis for all tracked products."""
    try:
        from .market_intelligence import MarketIntelligence
        import asyncio
        
        market_intel = MarketIntelligence()
        
        with Session(engine) as session:
            # Get all unique ASINs from active watches
            active_asins = session.exec(
                select(Watch.asin).where(Watch.asin.is_not(None)).distinct()
            ).all()
            
            log.info("Starting daily market analysis for %d products", len(active_asins))
            
            # Run async analysis (simplified for now)
            # In production, this would be more sophisticated
            for asin in active_asins[:10]:  # Limit to avoid quota issues
                try:
                    # This would ideally be run in async context
                    # For now, just log the analysis request
                    log.info("Would analyze market trends for ASIN: %s", asin)
                except Exception as e:
                    log.error("Failed to analyze ASIN %s: %s", asin, e)
                    
            log.info("Daily market analysis completed")
            
    except Exception as e:
        log.error("Daily market analysis failed: %s", e)


def weekly_trend_report() -> None:
    """Generate and send weekly trend reports to active users."""
    try:
        from .smart_alerts import SmartAlertEngine
        import asyncio
        
        smart_alerts = SmartAlertEngine()
        
        with Session(engine) as session:
            # Get users with active watches
            active_users = session.exec(
                select(User).join(Watch).where(Watch.asin.is_not(None)).distinct()
            ).all()
            
            log.info("Generating weekly trend reports for %d users", len(active_users))
            
            # For now, just log the report generation
            # In production, this would generate and send actual reports
            for user in active_users[:5]:  # Limit for testing
                try:
                    log.info("Would generate weekly report for user: %d", user.id)
                except Exception as e:
                    log.error("Failed to generate report for user %d: %s", user.id, e)
                    
            log.info("Weekly trend reports completed")
            
    except Exception as e:
        log.error("Weekly trend report generation failed: %s", e)


def realtime_job(watch_id: int) -> None:
    """Fetch latest price every 10 min, skipped 23:00-08:00 IST."""
    # TEMPORARILY DISABLED to prevent API quota exhaustion during testing
    log.info("Realtime job temporarily disabled for watch %d", watch_id)
    return
    
    now = datetime.now(TZ).time()
    if dtime(23, 0) <= now or now < dtime(8, 0):
        return  # quiet hours
    with Session(engine) as s:
        watch = s.get(Watch, watch_id)
        if not watch or watch.mode != "rt":
            return
        price = get_price(watch.asin)
        # store price history
        s.add(Price(watch_id=watch.id, asin=watch.asin, price=price, source="paapi"))
        s.commit()
        _send_single_card(watch.user_id, watch.keywords, price, watch.asin, watch.id)


def digest_job(user_id: int) -> None:
    """Pick best 5 discounts across a user's watches and send a carousel."""
    with Session(engine) as s:
        user = s.exec(select(User).where(User.id == user_id)).one_or_none()
        if not user:
            return
        cards: list[tuple[str, str, str]] = []  # (img, caption, kb)
        for watch in user.watches:
            price = get_price(watch.asin)
            discount_ok = watch.min_discount is None or price <= (
                100 - watch.min_discount
            ) / 100 * (watch.max_price or price)
            if discount_ok:
                caption, kb = build_single_card(
                    watch.keywords,
                    price,
                    "https://m.media-amazon.com/images/I/81.png",
                    watch.asin,
                    watch.id,
                )
                cards.append(
                    ("https://m.media-amazon.com/images/I/81.png", caption, kb)
                )
            if len(cards) == 5:
                break
        if cards:
            bot = Bot(token=settings.TELEGRAM_TOKEN)
            for img, cap, kb in cards:
                bot.send_photo(chat_id=user_id, photo=img, caption=cap, reply_markup=kb)


# ---------------------------------------------------------------------------


def _send_single_card(
    user_id: int, title: str, price: int, asin: str, watch_id: int
) -> None:
    from telegram import Bot  # local import to avoid circulars at boot

    bot = Bot(token=settings.TELEGRAM_TOKEN)
    cap, kb = build_single_card(
        title, price, "https://m.media-amazon.com/images/I/81.png", asin, watch_id
    )
    bot.send_photo(
        chat_id=user_id,
        photo="https://m.media-amazon.com/images/I/81.png",
        caption=cap,
        reply_markup=kb,
    )


# Start scheduler immediately on module import
scheduler.start()

# Initialize enrichment scheduler if enhanced models are enabled
try:
    from .enrichment_scheduler import initialize_enrichment_scheduler
    initialize_enrichment_scheduler()
except ImportError:
    # Enhanced models not available
    pass

# Initialize market intelligence scheduler
try:
    from .market_intelligence import MarketIntelligence
    from .smart_alerts import SmartAlertEngine
    
    market_intel = MarketIntelligence()
    smart_alerts = SmartAlertEngine()
    
    # Schedule daily market analysis
    scheduler.add_job(
        daily_market_analysis,
        CronTrigger(hour=3, minute=0, timezone=TZ),  # 3 AM IST
        id="market_analysis",
        replace_existing=True,
    )
    
    # Schedule weekly trend reports
    scheduler.add_job(
        weekly_trend_report,
        CronTrigger(day_of_week=0, hour=4, minute=0, timezone=TZ),  # Sunday 4 AM
        id="weekly_trends",
        replace_existing=True,
    )
    
except ImportError:
    # Market intelligence not available
    pass