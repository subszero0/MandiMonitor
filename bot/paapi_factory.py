"""PA-API client factory for safe migration between implementations.

This factory provides a centralized way to switch between the legacy
amazon-paapi implementation and the new official paapi5-python-sdk
implementation using a feature flag.
"""

from logging import getLogger
from typing import Protocol

from .config import settings

log = getLogger(__name__)


class PaapiClientProtocol(Protocol):
    """Protocol defining the PA-API client interface.
    
    This ensures both implementations provide the same methods.
    """
    
    async def get_item_detailed(
        self, asin: str, resources=None, priority: str = "normal"
    ):
        """Get detailed product information."""
        ...
        
    async def search_items_advanced(
        self,
        keywords=None,
        title=None,
        brand=None,
        search_index: str = "All",
        min_price=None,
        max_price=None,
        min_reviews_rating=None,
        min_savings_percent=None,
        merchant: str = "All",
        condition: str = "New",
        item_count: int = 10,
        item_page: int = 1,
        sort_by=None,
        browse_node_id=None,
        priority: str = "normal",
    ):
        """Search for products with advanced filtering."""
        ...
        
    async def get_browse_nodes_hierarchy(
        self, browse_node_id: int, priority: str = "normal"
    ):
        """Get browse nodes hierarchy."""
        ...


class LegacyPaapiClient:
    """Wrapper for the existing PA-API implementation.
    
    This class provides a consistent interface for the legacy implementation,
    allowing the factory to switch between implementations seamlessly.
    """
    
    def __init__(self):
        """Initialize the legacy PA-API client."""
        # Import here to avoid circular imports
        from . import paapi_enhanced
        self._paapi = paapi_enhanced
        
    async def get_item_detailed(
        self, asin: str, resources=None, priority: str = "normal"
    ):
        """Get detailed product information using legacy implementation."""
        return await self._paapi.get_item_detailed(asin, resources, priority)
        
    async def search_items_advanced(
        self,
        keywords=None,
        title=None,
        brand=None,
        search_index: str = "All",
        min_price=None,
        max_price=None,
        min_reviews_rating=None,
        min_savings_percent=None,
        merchant: str = "All",
        condition: str = "New",
        item_count: int = 10,
        item_page: int = 1,
        sort_by=None,
        browse_node_id=None,
        priority: str = "normal",
    ):
        """Search for products using legacy implementation."""
        return await self._paapi.search_items_advanced(
            keywords=keywords,
            title=title,
            brand=brand,
            search_index=search_index,
            min_price=min_price,
            max_price=max_price,
            min_reviews_rating=min_reviews_rating,
            min_savings_percent=min_savings_percent,
            merchant=merchant,
            condition=condition,
            item_count=item_count,
            item_page=item_page,
            sort_by=sort_by,
            browse_node_id=browse_node_id,
            priority=priority,
        )
        
    async def get_browse_nodes_hierarchy(
        self, browse_node_id: int, priority: str = "normal"
    ):
        """Get browse nodes hierarchy using legacy implementation."""
        return await self._paapi.get_browse_nodes_hierarchy(browse_node_id, priority)


def get_paapi_client() -> PaapiClientProtocol:
    """Get the appropriate PA-API client based on feature flag.
    
    Returns:
    -------
        PA-API client instance (either legacy or official SDK)
        
    Raises:
    ------
        ImportError: If the official SDK is not available when feature flag is enabled
        ValueError: If credentials are not properly configured
    """
    if settings.USE_NEW_PAAPI_SDK:
        log.info("Using official PA-API SDK (paapi5-python-sdk)")
        try:
            from .paapi_official import OfficialPaapiClient
            return OfficialPaapiClient()
        except ImportError as e:
            log.error("Failed to import official PA-API SDK: %s", e)
            log.warning("Falling back to legacy PA-API implementation")
            return LegacyPaapiClient()
    else:
        log.info("Using legacy PA-API implementation (amazon-paapi)")
        return LegacyPaapiClient()


# Convenience functions for backward compatibility
async def get_item_detailed(
    asin: str, resources=None, priority: str = "normal"
):
    """Get detailed product information using the active PA-API client."""
    client = get_paapi_client()
    return await client.get_item_detailed(asin, resources, priority)


async def search_items_advanced(
    keywords=None,
    title=None,
    brand=None,
    search_index: str = "All",
    min_price=None,
    max_price=None,
    min_reviews_rating=None,
    min_savings_percent=None,
    merchant: str = "All",
    condition: str = "New",
    item_count: int = 10,
    item_page: int = 1,
    sort_by=None,
    browse_node_id=None,
    priority: str = "normal",
):
    """Search for products using the active PA-API client."""
    client = get_paapi_client()
    return await client.search_items_advanced(
        keywords=keywords,
        title=title,
        brand=brand,
        search_index=search_index,
        min_price=min_price,
        max_price=max_price,
        min_reviews_rating=min_reviews_rating,
        min_savings_percent=min_savings_percent,
        merchant=merchant,
        condition=condition,
        item_count=item_count,
        item_page=item_page,
        sort_by=sort_by,
        browse_node_id=browse_node_id,
        priority=priority,
    )


async def get_browse_nodes_hierarchy(
    browse_node_id: int, priority: str = "normal"
):
    """Get browse nodes hierarchy using the active PA-API client."""
    client = get_paapi_client()
    return await client.get_browse_nodes_hierarchy(browse_node_id, priority)
