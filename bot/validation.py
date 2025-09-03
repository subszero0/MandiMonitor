"""Input validation utilities for MandiMonitor Bot."""

import re
from typing import Optional


class DevInputValidator:
    """Simple input validation for development phase."""

    @staticmethod
    def validate_search_query(query: str) -> Optional[str]:
        """Validate search queries with dev-friendly rules."""
        if not query or len(query) > 200:
            return None

        # Basic sanitization for dev
        clean_query = re.sub(r'[<>"\';]', '', query)
        return clean_query.strip()

    @staticmethod
    def validate_asin(asin: str) -> Optional[str]:
        """Validate ASIN format."""
        if not asin:
            return None

        # ASIN format: 10 alphanumeric characters
        if not re.match(r'^[A-Z0-9]{10}$', asin.upper()):
            return None

        return asin.upper()

    @staticmethod
    def validate_price_range(min_price: Optional[float], max_price: Optional[float]) -> tuple[Optional[float], Optional[float]]:
        """Validate price range parameters."""
        if min_price is not None and min_price < 0:
            return None, None
        if max_price is not None and max_price < 0:
            return None, None
        if min_price is not None and max_price is not None and min_price > max_price:
            return None, None

        return min_price, max_price

    @staticmethod
    def sanitize_telegram_message(text: str) -> str:
        """Sanitize telegram message content."""
        if not text:
            return ""

        # Remove potentially dangerous characters for dev
        clean_text = re.sub(r'[<>"\';]', '', text)
        return clean_text.strip()
