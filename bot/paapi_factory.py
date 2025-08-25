"""PA-API client factory using official Amazon SDK.

This factory provides access to the official paapi5-python-sdk implementation.
Legacy amazon-paapi support has been removed due to reliability issues.
"""

from logging import getLogger
from typing import Protocol

log = getLogger(__name__)


class PaapiClientProtocol(Protocol):
    """Protocol defining the PA-API client interface."""
    
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
        item_count: int = 30,
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


async def get_paapi_client() -> PaapiClientProtocol:
    """Get the official PA-API client.
    
    Returns:
    -------
        Official PA-API client instance using paapi5-python-sdk
        
    Raises:
    ------
        ImportError: If the official SDK is not available
        ValueError: If credentials are not properly configured
    """
    log.info("Using official PA-API SDK (paapi5-python-sdk)")
    from .paapi_official import OfficialPaapiClient
    return OfficialPaapiClient()


# Convenience functions for backward compatibility
async def get_item_detailed(
    asin: str, resources=None, priority: str = "normal"
):
    """Get detailed product information using the active PA-API client."""
    client = await get_paapi_client()
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
    item_count: int = 30,
    item_page: int = 1,
    sort_by=None,
    browse_node_id=None,
    priority: str = "normal",
):
    """Search for products using the active PA-API client."""
    client = await get_paapi_client()
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
    client = await get_paapi_client()
    return await client.get_browse_nodes_hierarchy(browse_node_id, priority)
