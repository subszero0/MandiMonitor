"""Amazon PA-API wrapper for product information."""

import asyncio
from logging import getLogger
from amazon_paapi import AmazonApi

from .config import settings
from .errors import QuotaExceededError

log = getLogger(__name__)


async def get_item(asin: str) -> dict:
    """Fetch product information from Amazon PA-API.

    Args:
        asin: Amazon Standard Identification Number

    Returns:
        Dict with price, title, image

    Raises:
        QuotaExceededError: When PA-API quota is exceeded
    """
    try:
        # Run PA-API call in thread since it's sync
        result = await asyncio.to_thread(_sync_get_item, asin)
        return result
    except Exception as exc:
        # Check if it's a quota exceeded error (HTTP 503)
        if "503" in str(exc) or "quota" in str(exc).lower():
            log.warning("PA-API quota exceeded for ASIN: %s", asin)
            raise QuotaExceededError(f"PA-API quota exceeded for {asin}") from exc
        log.error("PA-API error for ASIN %s: %s", asin, exc)
        raise


def _sync_get_item(asin: str) -> dict:
    """Synchronous PA-API call."""
    # Initialize API client
    api = AmazonApi(
        key=settings.PAAPI_ACCESS_KEY,
        secret=settings.PAAPI_SECRET_KEY,
        tag=settings.PAAPI_TAG,
        country="IN",
    )

    # Get item data
    try:
        items = api.get_items(asin)
        if not items:
            raise ValueError(f"No item found for ASIN: {asin}")

        item = items[0]

        # Extract price
        price_value = None
        if hasattr(item, "prices") and hasattr(item.prices, "price"):
            price_value = item.prices.price.value

        if not price_value:
            raise ValueError(f"No price found for ASIN: {asin}")

        # Extract other fields
        title = getattr(item, "title", "") or ""
        image_url = ""
        if hasattr(item, "images") and hasattr(item.images, "large"):
            image_url = item.images.large.url

        return {
            "price": int(float(price_value) * 100),  # Convert to paise
            "title": title,
            "image": image_url,
        }

    except Exception as e:
        log.error("PA-API call failed for ASIN %s: %s", asin, e)
        raise
