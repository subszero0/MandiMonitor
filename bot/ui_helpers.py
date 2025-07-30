"""Inline button builders."""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def build_brand_buttons(brands: list[str]) -> InlineKeyboardMarkup:
    """Build inline keyboard with brand selection buttons.

    Args:
    ----
        brands: List of brand names to create buttons for

    Returns:
    -------
        InlineKeyboardMarkup with brand buttons arranged in rows

    """
    # Create rows of 3 buttons each
    rows = []
    for i in range(0, len(brands), 3):
        row = [
            InlineKeyboardButton(
                brand.title(),
                callback_data=f"brand:{brand.lower()}",
            )
            for brand in brands[i : i + 3]
        ]
        rows.append(row)

    return InlineKeyboardMarkup(rows)


def build_discount_buttons() -> InlineKeyboardMarkup:
    """Build inline keyboard with discount percentage buttons.

    Returns
    -------
        InlineKeyboardMarkup with discount percentage options

    """
    percents = [10, 15, 20, 25, 30]
    buttons = [
        InlineKeyboardButton(
            f"{p}%",
            callback_data=f"disc:{p}",
        )
        for p in percents
    ]

    # Arrange in rows of 3
    rows = []
    for i in range(0, len(buttons), 3):
        rows.append(buttons[i : i + 3])

    # Add skip option
    rows.append([InlineKeyboardButton("Skip", callback_data="disc:skip")])

    return InlineKeyboardMarkup(rows)


def build_price_buttons() -> InlineKeyboardMarkup:
    """Build inline keyboard with common price ranges.

    Returns
    -------
        InlineKeyboardMarkup with price range options

    """
    prices = [
        ("Under ₹10k", 10000),
        ("Under ₹25k", 25000),
        ("Under ₹50k", 50000),
        ("Under ₹75k", 75000),
        ("Under ₹1L", 100000),
        ("Skip", 0),
    ]

    rows = []
    for i in range(0, len(prices), 2):
        row = [
            InlineKeyboardButton(
                text,
                callback_data=f"price:{amount}" if amount > 0 else "price:skip",
            )
            for text, amount in prices[i : i + 2]
        ]
        rows.append(row)

    return InlineKeyboardMarkup(rows)
