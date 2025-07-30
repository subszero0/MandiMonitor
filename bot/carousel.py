"""Telegram carousel message builder for product cards."""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def build_carousel(products: list) -> list:
    """Build Telegram carousel from product list.

    Args:
    ----
        products: List of product dictionaries

    Returns:
    -------
        List of Telegram media objects for carousel

    """


def build_single_card(
    title: str, price: int, image: str, asin: str
) -> tuple[str, InlineKeyboardMarkup]:
    """Build a single product card with caption and buy button.

    Args:
    ----
        title: Product title/name
        price: Current price in rupees
        image: Product image URL
        asin: Amazon ASIN for affiliate link

    Returns:
    -------
        Tuple of (caption_text, keyboard_markup)

    """
    # Build caption with price formatting
    caption = f"📱 {title}\n💰 ₹{price:,}\n\n🔥 Current best price!"

    # Build affiliate URL with proper Amazon affiliate tag
    affiliate_url = (
        f"https://www.amazon.in/dp/{asin}?tag=YOURTAG-21&linkCode=ogi&th=1&psc=1"
    )

    # Create buy button keyboard
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(text="🛒 BUY NOW", url=affiliate_url)],
        ]
    )

    return caption, keyboard


def build_deal_card(
    title: str,
    current_price: int,
    original_price: int,
    discount_percent: int,
    image: str,
    asin: str,
) -> tuple[str, InlineKeyboardMarkup]:
    """Build a deal card showing discount information.

    Args:
    ----
        title: Product title/name
        current_price: Current discounted price
        original_price: Original MRP
        discount_percent: Discount percentage
        image: Product image URL
        asin: Amazon ASIN for affiliate link

    Returns:
    -------
        Tuple of (caption_text, keyboard_markup)

    """
    # Build caption with deal information
    caption = (
        f"🔥 -{discount_percent}% DEAL!\n\n"
        f"📱 {title}\n"
        f"💰 ₹{current_price:,} (now)\n"
        f"💸 ₹{original_price:,} (was)\n"
        f"💵 You save ₹{original_price - current_price:,}\n\n"
        f"⚡ Limited time offer!"
    )

    # Build affiliate URL
    affiliate_url = (
        f"https://www.amazon.in/dp/{asin}?tag=YOURTAG-21&linkCode=ogi&th=1&psc=1"
    )

    # Create buy button keyboard
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(text="🛒 BUY NOW", url=affiliate_url)],
        ]
    )

    return caption, keyboard
