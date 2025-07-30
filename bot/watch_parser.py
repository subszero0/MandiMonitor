"""Parser for watch creation text input."""

from __future__ import annotations

from typing import Any, Dict, Optional

from .patterns import PAT_ASIN, PAT_BRAND, PAT_DISCOUNT, PAT_PRICE_UNDER


def parse_watch(text: str) -> Dict[str, Any]:
    """Extract watch fields from user input text.

    Args:
    ----
        text: User input text containing product description or Amazon link

    Returns:
    -------
        Dictionary with extracted fields: asin, brand, max_price, min_discount, keywords
        Missing fields will be None

    """
    # Extract ASIN from URL or standalone ASIN
    asin = None
    if match := PAT_ASIN.search(text):
        # Check both groups - group 1 for URL format, group 2 for standalone
        potential_asin = match.group(1) if match.group(1) else match.group(2)
        # Validate ASIN format (10 characters, starts with B)
        if (
            potential_asin
            and len(potential_asin) == 10
            and potential_asin.startswith("B")
        ):
            asin = potential_asin

    # Extract brand
    brand = None
    if match := PAT_BRAND.search(text):
        brand = match.group(1).lower().replace("-", " ").replace("_", " ")

    # Extract maximum price
    max_price = None
    if match := PAT_PRICE_UNDER.search(text):
        price_str = match.group(1).replace(",", "").replace(" ", "")
        try:
            if price_str.endswith("k"):
                max_price = int(float(price_str[:-1]) * 1000)
            elif price_str.endswith("000"):
                max_price = int(price_str)
            else:
                max_price = int(price_str)
        except (ValueError, TypeError):
            max_price = None

    # Extract minimum discount percentage
    min_discount = None
    if match := PAT_DISCOUNT.search(text):
        try:
            min_discount = int(match.group(1))
        except (ValueError, TypeError):
            min_discount = None

    return {
        "asin": asin,
        "brand": brand,
        "max_price": max_price,
        "min_discount": min_discount,
        "keywords": text.strip(),
    }


def normalize_price_input(price_text: str) -> Optional[int]:
    """Normalize price input from various formats.

    Args:
    ----
        price_text: Price text like "30k", "25000", "₹30,000"

    Returns:
    -------
        Normalized price as integer, or None if invalid

    """
    if not price_text:
        return None

    # Remove currency symbols and spaces
    cleaned = (
        price_text.replace("₹", "")
        .replace("rs.", "")
        .replace("rs", "")
        .replace(",", "")
        .replace(" ", "")
        .lower()
    )

    try:
        if cleaned.endswith("k"):
            return int(float(cleaned[:-1]) * 1000)
        elif cleaned.endswith("l"):
            return int(float(cleaned[:-1]) * 100000)
        elif cleaned.endswith("lac"):
            return int(float(cleaned[:-3]) * 100000)
        elif cleaned.endswith("lakh"):
            return int(float(cleaned[:-4]) * 100000)
        elif cleaned.endswith("cr"):
            return int(float(cleaned[:-2]) * 10000000)
        elif cleaned.endswith("crore"):
            return int(float(cleaned[:-5]) * 10000000)
        else:
            return int(cleaned)
    except (ValueError, TypeError):
        return None


def validate_watch_data(data: Dict[str, Any]) -> Dict[str, str]:
    """Validate watch data and return any validation errors.

    Args:
    ----
        data: Watch data dictionary

    Returns:
    -------
        Dictionary of field names to error messages

    """
    errors = {}

    # Validate ASIN format if provided
    if data.get("asin"):
        asin = data["asin"]
        if not (len(asin) == 10 and asin.startswith("B") and asin[1:].isalnum()):
            errors["asin"] = "Invalid ASIN format"

    # Validate price range
    if data.get("max_price") is not None:
        price = data["max_price"]
        if not isinstance(price, int) or price <= 0 or price > 10000000:
            errors["max_price"] = "Price must be between ₹1 and ₹1 crore"

    # Validate discount percentage
    if data.get("min_discount") is not None:
        discount = data["min_discount"]
        if not isinstance(discount, int) or discount < 1 or discount > 99:
            errors["min_discount"] = "Discount must be between 1% and 99%"

    # Validate keywords length
    if data.get("keywords"):
        if len(data["keywords"]) > 500:
            errors["keywords"] = "Description too long (max 500 characters)"
        elif len(data["keywords"].strip()) < 3:
            errors["keywords"] = "Description too short (min 3 characters)"

    return errors
