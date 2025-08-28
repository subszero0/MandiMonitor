"""Telegram carousel message builder for product cards."""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from typing import Dict, List, Any, Optional


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
    title: str, price: int, image: str, asin: str, watch_id: int
) -> tuple[str, InlineKeyboardMarkup]:
    """Build a single product card with caption and callback buy button.

    Args:
    ----
        title: Product title/name
        price: Current price in rupees (already in correct format)
        image: Product image URL
        asin: Amazon ASIN for affiliate link
        watch_id: Watch ID for click tracking

    Returns:
    -------
        Tuple of (caption_text, keyboard_markup)

    """
    # Escape Markdown special characters in title to prevent parsing errors
    escaped_title = title.replace("*", "\\*").replace("_", "\\_").replace("[", "\\[").replace("]", "\\]").replace("(", "\\(").replace(")", "\\)").replace("~", "\\~").replace("`", "\\`").replace(">", "\\>").replace("#", "\\#").replace("+", "\\+").replace("-", "\\-").replace("=", "\\=").replace("|", "\\|").replace("{", "\\{").replace("}", "\\}").replace(".", "\\.").replace("!", "\\!")
    
    # Build caption with proper price formatting (price is already in rupees, not paise)
    # Check if price needs conversion from paise to rupees
    display_price = price // 100 if price > 10000 else price
    caption = f"📱 {escaped_title}\n💰 ₹{display_price:,}\n\n🔥 Current best price!"

    # Create buy button with callback data for click tracking
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    text="🛒 BUY NOW", callback_data=f"click:{watch_id}:{asin}"
                )
            ],
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
    watch_id: int,
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
        watch_id: Watch ID for click tracking

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

    # Create buy button with callback data for click tracking
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    text="🛒 BUY NOW", callback_data=f"click:{watch_id}:{asin}"
                )
            ],
        ]
    )

    return caption, keyboard
