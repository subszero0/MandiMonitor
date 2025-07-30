"""Affiliate URL generation for Amazon links."""

from bot.config import settings


def build_affiliate_url(asin: str) -> str:
    """Build Amazon affiliate URL with tag and tracking parameters.

    Args:
    ----
        asin: Amazon Standard Identification Number

    Returns:
    -------
        Complete affiliate URL with tag and tracking parameters

    """
    base = f"https://www.amazon.in/dp/{asin}"
    tag = f"?tag={settings.PAAPI_TAG or 'YOURTAG-21'}"
    extra = "&linkCode=ogi&th=1&psc=1"
    return base + tag + extra
