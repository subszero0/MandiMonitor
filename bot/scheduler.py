"""BackgroundScheduler singleton & helpers."""

from __future__ import annotations
from datetime import datetime, time as dtime
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


def realtime_job(watch_id: int) -> None:
    """Fetch latest price every 10 min, skipped 23:00-08:00 IST."""
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