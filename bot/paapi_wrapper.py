"""Amazon PA-API wrapper for product information."""


def get_item(asin: str) -> dict | None:
    """Fetch product information from Amazon PA-API.
    
    Args:
        asin: Amazon Standard Identification Number
        
    Returns:
        Dict with price, title, image or None if not found
    """
    pass 