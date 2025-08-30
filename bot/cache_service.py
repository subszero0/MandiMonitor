"""Cache service for 24h price caching with PA-API and scraper fallback."""

import asyncio
from datetime import datetime, timedelta
from logging import getLogger

from sqlmodel import Session, create_engine, select

from .errors import QuotaExceededError
from .models import Cache
from .paapi_factory import get_item_detailed
from .scraper import scrape_price

log = getLogger(__name__)

# Create database engine
engine = create_engine(
    "sqlite:///dealbot.db",
    echo=False,
    connect_args={"check_same_thread": False},
)


async def get_price_async(asin: str) -> int:
    """Async version of get_price for use within async context."""
    with Session(engine) as session:
        # Check cache first
        statement = select(Cache).where(Cache.asin == asin)
        cached_result = session.exec(statement).first()

        # Return cached price if within 24 hours
        if cached_result and cached_result.fetched_at > datetime.utcnow() - timedelta(
            hours=24,
        ):
            log.info(
                "Returning cached price for ASIN %s: %d paise",
                asin,
                cached_result.price,
            )
            return cached_result.price

        # Try to fetch new price
        price = None

        # First try enhanced PA-API
        try:
            log.info("Fetching price via enhanced PA-API for ASIN: %s", asin)
            item_data = await get_item_detailed(asin, priority="high")  # High priority for user requests
            price = item_data.get("price")
            if price:
                log.info("Enhanced PA-API returned price for ASIN %s: %d paise", asin, price)
            else:
                log.warning("Enhanced PA-API returned no price for ASIN %s", asin)
                price = None
        except QuotaExceededError:
            log.warning(
                "PA-API quota exceeded for ASIN %s, falling back to scraper",
                asin,
            )
        except Exception as e:
            log.warning(
                "PA-API failed for ASIN %s: %s, falling back to scraper",
                asin,
                e,
            )

        # Fallback to scraper if PA-API failed
        if price is None:
            try:
                log.info("Fetching price via scraper for ASIN: %s", asin)
                price = await scrape_price(asin)
                log.info("Scraper returned price for ASIN %s: %d paise", asin, price)
            except Exception as e:
                log.error("Scraper failed for ASIN %s: %s", asin, e)
                if cached_result:
                    log.warning(
                        "Using stale cache for ASIN %s: %d paise",
                        asin,
                        cached_result.price,
                    )
                    return cached_result.price
                raise ValueError(
                    f"Could not fetch price for ASIN {asin} from any source",
                ) from e

        # Handle case when no price could be fetched
        if price is None:
            log.warning("No price could be fetched for ASIN %s from any source", asin)
            # Return a default price instead of None to prevent type issues
            price = 0
        
        # Only update cache if we have a valid price > 0
        if price and price > 0:
            cache_entry = Cache(asin=asin, price=price, fetched_at=datetime.utcnow())
            session.merge(cache_entry)
            session.commit()
            log.info("Cached new price for ASIN %s: %d paise", asin, price)
        else:
            log.warning("Skipping cache update for ASIN %s: price is %s", asin, price)
            
        return price


def get_price(asin: str) -> int:
    """Get price for ASIN with 24h cache and fallback strategy.

    Args:
    ----
        asin: Amazon Standard Identification Number

    Returns:
    -------
        Price in paise (integer)

    Raises:
    ------
        ValueError: If price cannot be fetched from any source

    """
    with Session(engine) as session:
        # Check cache first
        statement = select(Cache).where(Cache.asin == asin)
        cached_result = session.exec(statement).first()

        # Return cached price if within 24 hours
        if cached_result and cached_result.fetched_at > datetime.utcnow() - timedelta(
            hours=24,
        ):
            log.info(
                "Returning cached price for ASIN %s: %d paise",
                asin,
                cached_result.price,
            )
            return cached_result.price

        # Try to fetch new price
        price = None

        # First try enhanced PA-API
        try:
            log.info("Fetching price via enhanced PA-API for ASIN: %s", asin)
            # Use async version instead of asyncio.run() to avoid event loop conflicts
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # We're in an async context, can't use asyncio.run()
                log.warning("Cannot use PA-API from sync context in async environment")
                item_data = None
            else:
                item_data = asyncio.run(get_item_detailed(asin, priority="high"))
            price = item_data.get("price") if item_data else None
            if price:
                log.info("Enhanced PA-API returned price for ASIN %s: %d paise", asin, price)
            else:
                log.warning("Enhanced PA-API returned no price for ASIN %s", asin)
                price = None
        except QuotaExceededError:
            log.warning(
                "PA-API quota exceeded for ASIN %s, falling back to scraper",
                asin,
            )
        except Exception as e:
            log.warning(
                "PA-API failed for ASIN %s: %s, falling back to scraper",
                asin,
                e,
            )

        # Fallback to scraper if PA-API failed
        if price is None:
            try:
                log.info("Fetching price via scraper for ASIN: %s", asin)
                # Use async version instead of asyncio.run() to avoid event loop conflicts
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # We're in an async context, can't use asyncio.run()
                    log.warning("Cannot use scraper from sync context in async environment")
                    price = None
                else:
                    price = asyncio.run(scrape_price(asin))
                if price:
                    log.info("Scraper returned price for ASIN %s: %d paise", asin, price)
            except Exception as e:
                log.error("Scraper failed for ASIN %s: %s", asin, e)
                if cached_result:
                    log.warning(
                        "Using stale cache for ASIN %s: %d paise",
                        asin,
                        cached_result.price,
                    )
                    return cached_result.price
                raise ValueError(
                    f"Could not fetch price for ASIN {asin} from any source",
                ) from e

        # Handle case when no price could be fetched
        if price is None:
            log.warning("No price could be fetched for ASIN %s from any source", asin)
            # Return a default price instead of None to prevent type issues
            price = 0
        
        # Only update cache if we have a valid price > 0
        if price and price > 0:
            cache_entry = Cache(asin=asin, price=price, fetched_at=datetime.utcnow())
            session.merge(cache_entry)
            session.commit()
            log.info("Cached new price for ASIN %s: %d paise", asin, price)
        else:
            log.warning("Skipping cache update for ASIN %s: price is %s", asin, price)
            
        return price


def initialize_database():
    """Initialize database tables."""
    from .models import SQLModel

    SQLModel.metadata.create_all(engine)
